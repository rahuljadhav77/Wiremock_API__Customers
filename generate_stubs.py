import argparse
import json
import re
from pathlib import Path

import google.generativeai as genai

import os

# Load API key from environment variable — never hardcode secrets
_api_key = os.environ.get("GEMINI_API_KEY", "")
if not _api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set.\n"
        "Set it in your shell or add it to a .env file (never commit the key)."
    )
genai.configure(api_key=_api_key)

model = genai.GenerativeModel('models/gemma-4-31b-a4b-it')  # Using Gemma 4 31B


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
            
    # If no blocks, find the last { that looks like it starts a request
    start = text.rfind('{\n  "request":')
    if start == -1:
        start = text.rfind('{\n    "request":')
    if start == -1:
        start = text.rfind('{"request":')
    if start == -1:
        start = text.rfind('{')

    if start != -1:
        end = text.rfind('}') + 1
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except Exception:
            # Fallback for Gemma's chatty outputs: it usually puts the final json at the very end.
            lines = candidate.splitlines()
            for i in range(len(lines)):
                try:
                    return json.loads('\n'.join(lines[i:]))
                except Exception:
                    pass
    
    raise ValueError(f"No valid JSON found in model output.")


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


def generate_new_api_stub(request_description: str, response_description: str) -> dict:
    prompt = build_prompt(request_description, response_description)
    response = model.generate_content(prompt)
    return extract_json(response.text)


def infer_mapping_file(request_text: str) -> Path:
    path = extract_request_path(request_text)
    if not path:
        return Path("wiremock/mappings/rates-api.json")

    normalized = path.split("?")[0].strip("/").split("/")[0].lower()
    if "customers" in path:
        return Path("wiremock/mappings/customer-api.json")
    if "loans" in path:
        return Path("wiremock/mappings/loans-api.json")
    if "rates" in path:
        return Path("wiremock/mappings/rates-api.json")
    if "menu" in path:
        return Path("wiremock/mappings/menu-api.json")
    if normalized:
        return Path(f"wiremock/mappings/{normalized}-api.json")
    return Path("wiremock/mappings/rates-api.json")


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
        mapping_file.write_text(json.dumps({"mappings": []}, indent=2), encoding="utf-8")

    data = json.loads(mapping_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "mappings" not in data or not isinstance(data["mappings"], list):
        raise ValueError(f"Invalid mapping file format: {mapping_file}")

    data["mappings"].append(stub)
    mapping_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
    print(json.dumps(stub, indent=2))

    mapping_file = Path(args.mapping_file) if args.mapping_file else infer_mapping_file(request_text)
    if args.write:
        append_stub_to_mapping_file(stub, mapping_file)
        print(f"\nWrote new stub to {mapping_file}")
    else:
        print(f"\nMapping file not written. Use --write to save to {mapping_file}.")


if __name__ == "__main__":
    main()


