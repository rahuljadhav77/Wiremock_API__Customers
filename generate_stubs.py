import argparse
import json
import re
from pathlib import Path

import google.generativeai as genai

import os
from dotenv import load_dotenv

# Load API key from environment variable or .env file
load_dotenv()
_api_key = os.environ.get("GEMINI_API_KEY", "")
if not _api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set.\n"
        "Set it in your shell or add it to a .env file (never commit the key)."
    )
genai.configure(api_key=_api_key)

model = genai.GenerativeModel('gemma-4-31b-it')  # Using Gemma 4 31B

def load_text(value: str) -> str:
    path = Path(value)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return value.strip()


def extract_json(text: str) -> dict:
    text = text.strip()
    import re
    # Look for JSON blocks
    blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    for block in reversed(blocks):
        try:
            return json.loads(block)
        except Exception:
            pass
            
    # Try to find the largest JSON-like structure
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except Exception:
            # Try to fix common issues like trailing commas or multiple objects
            # but usually it's better to ask for a retry.
            pass
    
    raise ValueError(f"No valid JSON found in model output. Raw output start: {text[:100]}...")


def build_prompt(request_text: str, response_text: str) -> str:
    return f"""
You are a WireMock mapping generator.
Generate a valid WireMock mapping JSON object for this request and response.
Do not include markdown, explanation, or extra text.

Request description:
{request_text}

Response body:
{response_text}

Output only the JSON object for the mapping.
Use `urlPath` or `urlPathPattern` as appropriate.
Use `jsonBody` for the response body.
"""


def generate_new_api_stub(request_description: str, response_description: str, max_retries: int = 5) -> dict:
    prompt = build_prompt(request_description, response_description)
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"      🔄 Retry attempt {attempt} due to previous error: {last_error}")
                # Append the error to the prompt for self-correction if it's a parsing error
                if "JSON" in str(last_error):
                    current_prompt = f"{prompt}\n\nIMPORTANT: Your previous attempt failed with error: {last_error}. Please ensure the output is VALID JSON and strictly follows the WireMock format."
                else:
                    current_prompt = prompt
            else:
                current_prompt = prompt

            response = model.generate_content(current_prompt)
            if not response.text:
                raise ValueError("Empty response from AI model")
            
            return extract_json(response.text)
        except Exception as e:
            last_error = str(e)
            wait_time = (2 ** attempt) + 1
            if "503" in str(e) or "429" in str(e) or "quota" in str(e).lower() or "capacity" in str(e).lower():
                print(f"      ⚠️ Rate limit or capacity hit ({last_error}). Waiting {wait_time * 5}s...")
                import time
                time.sleep(wait_time * 5) # Longer wait for rate limits/capacity
            else:
                import time
                time.sleep(wait_time)
            
    raise RuntimeError(f"Failed to generate valid stub after {max_retries} attempts. Last error: {last_error}")


def infer_mapping_file(request_text: str) -> Path:
    root_dir = Path(__file__).resolve().parent
    path = extract_request_path(request_text)
    base_mappings = root_dir / "wiremock" / "mappings"
    
    if not path:
        return base_mappings / "rates-api.json"

    normalized = path.split("?")[0].strip("/").split("/")[0].lower()
    if "customers" in path:
        return base_mappings / "customer-api.json"
    if "loans" in path:
        return base_mappings / "loans-api.json"
    if "rates" in path:
        return base_mappings / "rates-api.json"
    if "menu" in path:
        return base_mappings / "menu-api.json"
    if normalized:
        return base_mappings / f"{normalized}-api.json"
    return base_mappings / "rates-api.json"


def extract_request_path(request_text: str) -> str:
    request_text = request_text.strip()
    match = re.search(r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s]*)", request_text, re.IGNORECASE)
    if match:
        return match.group(2)
    match = re.search(r"urlPath(?:Pattern)?\s*[:=]\s*\"([^\"]+)\"", request_text)
    if match:
        return match.group(1)
    return ""


def append_stub_to_mapping_file(stub: dict, mapping_file: Path) -> None:
    if not mapping_file.exists():
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        mapping_file.write_text(json.dumps({"mappings": []}, indent=2, ensure_ascii=False), encoding="utf-8")

    data = json.loads(mapping_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "mappings" not in data or not isinstance(data["mappings"], list):
        raise ValueError(f"Invalid mapping file format: {mapping_file}")

    data["mappings"].append(stub)
    mapping_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_and_write_stub(request_description: str, response_description: str, mapping_path: str) -> dict:
    stub = generate_new_api_stub(request_description, response_description)
    append_stub_to_mapping_file(stub, Path(mapping_path))
    return stub


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a WireMock mapping stub using Gemma 4.")
    parser.add_argument("--mapping-file", default=None, help="WireMock mapping file to append the new stub to")
    parser.add_argument("--request-desc", required=True, help="Description of the request pattern or request JSON file path")
    parser.add_argument("--response-desc", required=True, help="Description of the response body or response JSON file path")
    parser.add_argument("--write", action="store_true", help="Write the generated stub to the mapping file")

    args = parser.parse_args()
    request_text = load_text(args.request_desc)
    response_text = load_text(args.response_desc)

    stub = generate_new_api_stub(request_text, response_text)
    print(json.dumps(stub, indent=2, ensure_ascii=False))

    mapping_file = Path(args.mapping_file) if args.mapping_file else infer_mapping_file(request_text)
    if args.write:
        append_stub_to_mapping_file(stub, mapping_file)
        print(f"\nWrote new stub to {mapping_file}")
    else:
        print(f"\nMapping file not written. Use --write to save to {mapping_file}.")


if __name__ == "__main__":
    main()


