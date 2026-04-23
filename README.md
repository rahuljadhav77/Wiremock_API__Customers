# Customer API with WireMock + Excel (or CSV)

Traffic hits **WireMock** on port **8080**. WireMock **reverse-proxies** `/customers*` to a **Flask** service on port **5001**, which reads and writes a data file—**Excel `.xlsx` by default**, or **`.csv`** if you point `CUSTOMER_DATA_PATH` at a CSV path.

## Prerequisites

- Java 17+ (WireMock standalone JAR)
- Python 3 with `pip` (backend installs `openpyxl` for Excel)

## Install WireMock

The standalone JAR lives at `tools/wiremock-standalone-3.9.1.jar`. To download again:

```powershell
powershell -NoProfile -Command "New-Item -ItemType Directory -Path '.\tools' -Force | Out-Null; Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/org/wiremock/wiremock-standalone/3.9.1/wiremock-standalone-3.9.1.jar' -OutFile '.\tools\wiremock-standalone-3.9.1.jar'"
```

## Data file

### Default: Excel `.xlsx`

- **Path:** `backend/data/customers.xlsx`
- **Sheet:** first (active) sheet
- **Row 1:** column headers, in this exact order:  
  `customer_id`, `first_name`, `last_name`, `email`, `phone`, `status`, `registered_at`
- **Row 2+:** one customer per row  
- Edit in Excel, save as `.xlsx`. **Restart the backend** if it has the file open locked (or close Excel first).
- If the file is **missing or empty**, the app creates it with three sample rows on first startup.

### Optional: CSV

- Set **`CUSTOMER_DATA_PATH`** to a path ending in `.csv` (UTF-8).
- Same column names as header row; commas as delimiter.

## Run everything (recommended)

```powershell
.\start-all.ps1
```

## Run components separately

**Terminal 1 — backend:**

```powershell
.\start-backend.ps1
```

**Terminal 2 — WireMock:**

```powershell
.\start-wiremock.ps1
```

## Where to see the live APIs

Use the **same two endpoints** in both “run on PC” and Docker modes; only how you start the stack changes.

| What | URL / location |
|------|----------------|
| **GET** customer | `http://127.0.0.1:8080/customers/{id}` (through WireMock) |
| **POST** customer | `http://127.0.0.1:8080/customers` with JSON body |
| WireMock admin | `http://127.0.0.1:8080/__admin` |
| Browser docs (static) | Open `api-visualizer.html` from this folder |
| OpenAPI YAML | `openapi/customer-api.yaml` |
| Live Swagger UI (Docker only) | `http://127.0.0.1:8081` |

**Run on your machine (no Docker):** start the backend and WireMock (`.\start-all.ps1`), then use the **8080** URLs above. Backend health (optional): `http://127.0.0.1:5001/health`.

**Run in Docker:** start **Docker Desktop**, then see [Run everything in Docker](#run-everything-in-docker) below—then use the same **8080** URLs; Swagger UI is on **8081**.

## Example calls (through WireMock)

```powershell
curl.exe -s http://127.0.0.1:8080/customers/cust-001
curl.exe -s -X POST http://127.0.0.1:8080/customers -H "Content-Type: application/json" --data-binary "@sample-create-customer.json"
```

## Stop

- `.\stop-wiremock.ps1` — WireMock only  
- `.\stop-backend.ps1` — backend only  
- `.\stop-all.ps1` — both  

## Logs

- Backend logs (which API route was triggered): `backend/logs/backend.log`
- WireMock logs (proxy requests/responses): `logs/wiremock.log`

To watch in real time (PowerShell):

```powershell
Get-Content -Path .\backend\logs\backend.log -Wait -Tail 50
```

In another terminal:

```powershell
Get-Content -Path .\logs\wiremock.log -Wait -Tail 50
```

If you run the stack with Docker Compose, use container logs instead:

```powershell
docker compose logs -f customer-backend wiremock
```

## Monitor UI (localhost dashboard)

A small responsive web UI to **see status**, **start/stop** WireMock and the backend, inspect **versions**, and run **`docker compose pull`**.

- **Start UI:** `.\start-monitor-ui.ps1`
- **Open:** `http://127.0.0.1:5055` (listens on **localhost only**)
- **Stop UI:** `.\stop-monitor-ui.ps1`
- **Change port:** `$env:MONITOR_PORT="5056"; .\start-monitor-ui.ps1`

**Version label:** edit the project file `VERSION` (e.g. `1.0.0`) to bump what the dashboard shows as the bundle version. The UI also shows the WireMock JAR version (from `tools/`), `docker-compose.yml` image tags, and a snippet of `backend/requirements.txt`.

## How it works

- **On the host:** `wiremock/mappings/customer-api.json` **proxies** `/customers*` to `http://127.0.0.1:5001`.
- **In Docker:** `wiremock/mappings-docker/customer-api.json` proxies to `http://customer-backend:5001` (the Flask container on the Compose network).
- `backend/app.py` loads/saves rows via **openpyxl** (`.xlsx`/`.xlsm`) or **csv** module (`.csv`). POST appends a row; duplicate email → `409`. A lock serializes file updates.

## Run everything in Docker

Requires **Docker Desktop** (or another engine) running so `docker compose` can pull images and create containers.

From `C:\Users\pc\wiremock-customer-api`:

```powershell
docker compose up --build -d
```

- **API (WireMock → backend):** `http://127.0.0.1:8080` — e.g. `GET http://127.0.0.1:8080/customers/cust-001`
- **Swagger UI:** `http://127.0.0.1:8081`
- **WireMock admin:** `http://127.0.0.1:8080/__admin`

Customer Excel data inside the backend container is stored in the **`customer-data`** Docker volume (persists across restarts).

Stop and remove containers:

```powershell
docker compose down
```

To remove the named volume as well (wipe stored `.xlsx` data):

```powershell
docker compose down -v
```

### Docker layout

| Piece | Role |
|-------|------|
| `customer-backend` | Image built from `backend/Dockerfile`; listens on **5001** inside the network |
| `wiremock` | Published **8080**; mappings from `wiremock/mappings-docker/` |
| `swagger-ui` | Published **8081**; serves `openapi/customer-api.yaml` |
