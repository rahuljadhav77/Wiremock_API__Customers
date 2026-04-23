import argparse
import json
import os
import sys
from pathlib import Path

# Import the existing generation logic
import generate_stubs

try:
    import yaml
except ImportError:
    yaml = None

def process_openapi(file_path: Path):
    """Parses an OpenAPI/Swagger file and autonomously generates stubs for all endpoints."""
    print(f"🤖 Agent starting: Parsing OpenAPI spec from {file_path}")
    
    if file_path.suffix in ['.yaml', '.yml']:
        if not yaml:
            print("PyYAML is required to parse YAML files. Please run: pip install pyyaml")
            sys.exit(1)
        with open(file_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)

    paths = spec.get("paths", {})
    if not paths:
        print("No paths found in the OpenAPI spec.")
        return

    total_generated = 0

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                continue
            
            print(f"\n🔍 Analyzing: {method.upper()} {path}")
            
            # Construct a rich request description for the AI
            summary = details.get("summary", "")
            description = details.get("description", "")
            req_desc = f"{method.upper()} {path}\nSummary: {summary}\nDescription: {description}"
            
            # Extract parameters if any to give AI context on URL patterns
            parameters = details.get("parameters", [])
            if parameters:
                req_desc += "\nParameters:\n"
                for param in parameters:
                    req_desc += f"- {param.get('name')} ({param.get('in')}): {param.get('description', '')}\n"

            responses = details.get("responses", {})
            for status_code, resp_details in responses.items():
                print(f"  ⚡ Generating mock for status {status_code}...")
                
                resp_desc = f"Status Code: {status_code}\n"
                resp_desc += f"Description: {resp_details.get('description', '')}\n"
                
                # Extract example or schema if available
                content = resp_details.get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    example = content["application/json"].get("example", {})
                    if example:
                        resp_desc += f"Example JSON to return: {json.dumps(example)}\n"
                    else:
                        resp_desc += f"Response Schema: {json.dumps(schema)}\n"
                
                try:
                    # 1. Ask the LLM to generate the WireMock JSON
                    stub = generate_stubs.generate_new_api_stub(req_desc, resp_desc)
                    
                    # Fallback validation: Ensure status code matches if the AI missed it
                    if "response" in stub and "status" not in stub["response"] and status_code.isdigit():
                        stub["response"]["status"] = int(status_code)
                    
                    # 2. Autonomously route the stub to the correct mapping file
                    mapping_file = generate_stubs.infer_mapping_file(req_desc)
                    
                    # 3. Append to the file
                    generate_stubs.append_stub_to_mapping_file(stub, mapping_file)
                    
                    print(f"    ✅ Successfully appended to {mapping_file}")
                    total_generated += 1
                except Exception as e:
                    print(f"    ❌ Error generating stub for {method.upper()} {path}: {e}")

    print(f"\n🎉 Agent finished! Autonomously generated {total_generated} stubs.")

def process_json_pairs(directory: Path):
    """Autonomously scans a directory for JSON request/response pairs to generate stubs."""
    print(f"🤖 Agent starting: Scanning {directory} for JSON pairs")
    
    # A simple convention: any file named req_*.json should have a matching res_*.json
    req_files = list(directory.glob("req_*.json"))
    if not req_files:
        print("No request files found matching 'req_*.json'")
        return

    total_generated = 0
    for req_file in req_files:
        identifier = req_file.stem.replace("req_", "")
        res_file = directory / f"res_{identifier}.json"
        
        if not res_file.exists():
            print(f"  ⚠️ Skipping {req_file.name}: No matching {res_file.name} found.")
            continue
            
        print(f"\n🔍 Processing pair: {req_file.name} -> {res_file.name}")
        
        req_desc = req_file.read_text(encoding='utf-8')
        resp_desc = res_file.read_text(encoding='utf-8')
        
        try:
            stub = generate_stubs.generate_new_api_stub(req_desc, resp_desc)
            mapping_file = generate_stubs.infer_mapping_file(req_desc)
            generate_stubs.append_stub_to_mapping_file(stub, mapping_file)
            print(f"    ✅ Successfully appended to {mapping_file}")
            total_generated += 1
        except Exception as e:
            print(f"    ❌ Error generating stub for {identifier}: {e}")

    print(f"\n🎉 Agent finished! Autonomously generated {total_generated} stubs.")

def main():
    parser = argparse.ArgumentParser(description="Autonomous WireMock Stub Agent")
    parser.add_argument("--swagger", help="Path to Swagger/OpenAPI file (YAML or JSON)")
    parser.add_argument("--json-dir", help="Path to directory containing req_*.json and res_*.json files")
    
    args = parser.parse_args()
    
    if args.swagger:
        file_path = Path(args.swagger)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)
        process_openapi(file_path)
    elif args.json_dir:
        dir_path = Path(args.json_dir)
        if not dir_path.is_dir():
            print(f"Directory not found: {dir_path}")
            sys.exit(1)
        process_json_pairs(dir_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
