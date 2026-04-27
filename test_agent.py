import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise ValueError("GEMINI_API_KEY not found in environment")

genai.configure(api_key=_api_key)
model = genai.GenerativeModel('gemma-4-31b-it')

def extract_json(text: str) -> dict:
    """Robustly extract JSON from AI response text."""
    # Try to find content within triple backticks first
    code_block = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)
    
    # Then find the outermost braces
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:100]}...")
    
    clean_json = match.group(1)
    # Remove potential trailing text after the last }
    last_brace = clean_json.rfind('}')
    if last_brace != -1:
        clean_json = clean_json[:last_brace+1]
        
    return json.loads(clean_json)

def run_test_agent(stub_json: dict, wiremock_url: str = "http://127.0.0.1:8080") -> dict:
    """
    Analyzes the stub, determines the best test case, executes it, and verifies the result.
    """
    logs = []
    def log_step(msg):
        print(f"AGENT: {msg}")
        logs.append(msg)

    log_step("Test Agent starting...")
    
    # Phase 1: Planning the test case
    log_step("Analyzing stub structure and patterns...")
    plan_prompt = f"""
    You are a QA Automation Agent for WireMock.
    Analyze this WireMock stub and determine the test case.
    
    IMPORTANT: Your response must be ONLY a valid JSON object. 
    Do NOT include any preamble, explanations, or Markdown formatting outside the JSON.

    Stub:
    {json.dumps(stub_json, indent=2)}

    Required JSON structure:
    {{
        "url_path": "/sample/path",
        "method": "GET",
        "headers": {{}},
        "query_params": {{}},
        "expected_status": 200
    }}
    """
    
    try:
        plan_response = model.generate_content(plan_prompt)
        raw_plan = extract_json(plan_response.text)
        
        # Normalize keys to lowercase to be case-insensitive
        test_plan = {k.lower(): v for k, v in raw_plan.items()}
        
        # Safe extraction with defaults
        method = test_plan.get("method", "GET").upper()
        url_path = test_plan.get("url_path") or test_plan.get("url") or "/"
        headers = test_plan.get("headers", {})
        query_params = test_plan.get("query_params", {})
        expected_status = test_plan.get("expected_status", 200)

        log_step(f"Test Plan Formulated: {method} {url_path}")

        # Phase 2: Execute the test
        log_step(f"Executing request to {wiremock_url}...")
        full_url = f"{wiremock_url.rstrip('/')}{url_path}"
        if query_params:
            from urllib.parse import urlencode
            full_url += "?" + urlencode(query_params)

        req = urllib.request.Request(
            full_url, 
            method=method,
            headers=headers
        )
        
        test_result = {
            "url": full_url,
            "method": method,
            "expected_status": expected_status,
            "actual_status": None,
            "actual_body": None,
            "passed": False,
            "analysis": ""
        }

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                test_result["actual_status"] = resp.status
                test_result["actual_body"] = resp.read().decode("utf-8")
                log_step(f"Request successful. Received status {resp.status}")
        except urllib.error.HTTPError as e:
            test_result["actual_status"] = e.code
            test_result["actual_body"] = e.read().decode("utf-8")
            log_step(f"Request returned error status {e.code} (this may be expected)")
        except Exception as e:
            log_step(f"Network error: {str(e)}")
            return {"ok": False, "message": f"Network error during test: {str(e)}", "logs": logs}

        # Phase 3: AI Verification
        log_step("Initiating AI Verification phase...")
        verify_prompt = f"""
        Analyze the test result against the WireMock stub.
        
        IMPORTANT: Your response must be ONLY a valid JSON object. 
        Do NOT include any preamble or Markdown formatting.

        Stub Expected Response:
        {json.dumps(stub_json.get('response', {}), indent=2)}

        Actual Test Result:
        Status: {test_result['actual_status']}
        Body: {test_result['actual_body']}

        Did the test pass? (Status must match, body should be similar).
        Output ONLY a JSON object:
        {{
            "passed": true/false,
            "analysis": "Reasoning..."
        }}
        """
        
        verify_response = model.generate_content(verify_prompt)
        v_data = extract_json(verify_response.text)
        test_result["passed"] = v_data.get("passed", False)
        test_result["analysis"] = v_data.get("analysis", "")
        log_step(f"Verification complete: {'PASSED' if test_result['passed'] else 'FAILED'}")
        log_step(f"Reasoning: {test_result['analysis']}")
        
        return {
            "ok": True,
            "plan": test_plan,
            "result": test_result,
            "logs": logs
        }

    except Exception as e:
        log_step(f"Test Agent Error: {str(e)}")
        return {"ok": False, "message": str(e), "logs": logs}

if __name__ == "__main__":
    # Quick test
    sample_stub = {
        "request": {"method": "GET", "urlPath": "/health"},
        "response": {"status": 200, "jsonBody": {"status": "UP"}}
    }
    print(run_test_agent(sample_stub))
