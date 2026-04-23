# WireMock Customer API — with AI Stub Generator

A fully-featured WireMock mock API platform for customer data, with an **AI-powered autonomous stub generator** using Google's **Gemma 4 31B** model.

Traffic hits **WireMock** on port **8080**. WireMock **reverse-proxies** `/customers*` to a **Flask** backend on port **5001**, which reads and writes an Excel `.xlsx` or `.csv` data file.

---

## Prerequisites

- **Java 17+** — for WireMock standalone JAR
- **Python 3.10+** with `pip`
- **Google Gemini API Key** — for AI stub generation ([get one free here](https://aistudio.google.com/app/apikey))

---

## Quick Start

### 1. Set your API Key

Create a `.env` file (or set the environment variable in PowerShell):

```powershell
# Option A: Set in current PowerShell session
$env:GEMINI_API_KEY = "your_api_key_here"

# Option B: Copy the example file and fill in your key (never commit .env)
Copy-Item .env.example .env
```

### 2. Install WireMock JAR

```powershell
powershell -NoProfile -Command "New-Item -ItemType Directory -Path '.\tools' -Force | Out-Null; Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/org/wiremock/wiremock-standalone/3.9.1/wiremock-standalone-3.9.1.jar' -OutFile '.\tools\wiremock-standalone-3.9.1.jar'"
```

### 3. Start everything

```powershell
.\start-all.ps1
```

---

## AI Stub Generator

### Option A — Web UI (recommended)

Start the Monitor UI, then open the Stub Generator in your browser:

```powershell
.\start-monitor-ui.ps1
```

Open: **`http://127.0.0.1:5055/stub-generator`**

The UI has two tabs:

| Tab | What you provide | What happens |
|-----|-----------------|--------------|
| **Swagger / OpenAPI** | Upload a `.yaml`, `.yml`, or `.json` OpenAPI spec | Agent reads every endpoint + status code, generates and saves all stubs automatically |
| **JSON Request & Response** | Paste a request description and expected response | "Preview" shows the stub; "Generate & Save" writes it to the correct mapping file |

### Option B — Command Line (autonomous agent)

```powershell
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Generate stubs from a Swagger/OpenAPI file
python agent_stub_generator.py --swagger openapi/customer-api.yaml

# Generate stubs from a folder of JSON request/response pairs
# Files must be named: req_<name>.json + res_<name>.json
python agent_stub_generator.py --json-dir .\my-stubs\
```

The agent will:
1. Parse every endpoint and response scenario
2. Ask **Gemma 4 31B** to generate a valid WireMock mapping
3. Auto-route each stub to the correct mapping file (`customer-api.json`, `loans-api.json`, etc.)
4. Append the stubs without overwriting existing ones

---

## Live API Endpoints

| What | URL |
|------|-----|
| GET customer | `http://127.0.0.1:8080/customers/{id}` |
| POST customer | `http://127.0.0.1:8080/customers` |
| WireMock admin | `http://127.0.0.1:8080/__admin` |
| Monitor dashboard | `http://127.0.0.1:5055` |
| AI Stub Generator UI | `http://127.0.0.1:5055/stub-generator` |
| Backend health | `http://127.0.0.1:5001/health` |
| OpenAPI spec | `openapi/customer-api.yaml` |

### Example calls

```powershell
# GET a customer
curl.exe -s http://127.0.0.1:8080/customers/cust-001

# POST a new customer
curl.exe -s -X POST http://127.0.0.1:8080/customers -H "Content-Type: application/json" --data-binary "@sample-create-customer.json"
```

---

## Monitor UI

A local web dashboard to start/stop services, inspect versions, and trigger AI stub generation.

```powershell
.\start-monitor-ui.ps1       # Start
.\stop-monitor-ui.ps1        # Stop
```

Open: `http://127.0.0.1:5055`

Change port:
```powershell
$env:MONITOR_PORT="5056"; .\start-monitor-ui.ps1
```

---

## Data File

- **Default path:** `backend/data/customers.xlsx`
- **Required columns (Row 1):** `customer_id`, `first_name`, `last_name`, `email`, `phone`, `status`, `registered_at`
- **CSV alternative:** set `CUSTOMER_DATA_PATH` to a `.csv` file path

If the file is missing, the backend creates it with sample rows on first startup.

---

## Start / Stop Individual Services

```powershell
.\start-backend.ps1       # Flask backend (port 5001)
.\start-wiremock.ps1      # WireMock (port 8080)
.\start-monitor-ui.ps1    # Monitor dashboard (port 5055)
.\stop-all.ps1            # Stop everything
```

---

## Logs

```powershell
# Watch backend log
Get-Content -Path .\backend\logs\backend.log -Wait -Tail 50

# Watch WireMock log
Get-Content -Path .\logs\wiremock.log -Wait -Tail 50
```

---

## Run in Docker

```powershell
docker compose up --build -d
```

| Service | Port | Role |
|---------|------|------|
| `wiremock` | 8080 | Mock API gateway |
| `customer-backend` | 5001 (internal) | Flask data API |
| `swagger-ui` | 8081 | OpenAPI docs |

```powershell
docker compose down       # Stop
docker compose down -v    # Stop + wipe data volume
```

---

## Project Structure

```
wiremock-customer-api/
├── agent_stub_generator.py     # Autonomous AI stub generation agent
├── generate_stubs.py           # Core AI integration (Gemma 4 31B)
├── openapi/                    # OpenAPI specs
├── wiremock/mappings/          # WireMock stub mappings (local)
├── wiremock/mappings-docker/   # WireMock stub mappings (Docker)
├── backend/                    # Flask Customer API
├── monitor-ui/                 # Dashboard + AI Stub Generator UI
│   ├── app.py                  # Flask routes
│   └── templates/
│       ├── dashboard.html      # Service monitor
│       └── stub_generator.html # AI Stub Generator UI
├── .env.example                # Copy to .env and add your API key
└── start-all.ps1               # One-command startup
```

---

## Security Notes

- **Never commit `.env`** — it is already blocked by `.gitignore`
- `GEMINI_API_KEY` must be set as an environment variable before running the AI features
- The Monitor UI binds to `127.0.0.1` only — never expose it to a public network
