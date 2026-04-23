"""
Local control dashboard: status, versions, start/stop scripts.
Binds to 127.0.0.1 only — do not expose to a network.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MONITOR_PORT = int(os.environ.get("MONITOR_PORT", "5055"))


def _http_json(url: str, timeout: float = 2.0) -> tuple[bool, object]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return True, json.loads(body)
            except json.JSONDecodeError:
                return True, body
    except Exception as exc:  # noqa: BLE001 — surface any failure to UI
        return False, str(exc)


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


def status_wiremock() -> dict:
    ok, data = _http_json("http://127.0.0.1:8080/__admin/version")
    version = None
    if ok and isinstance(data, dict):
        version = data.get("version") or data.get("Version")
    if not ok:
        up = _http_ok("http://127.0.0.1:8080/__admin/mappings")
        return {"up": up, "version": version, "admin_error": str(data)}
    return {"up": True, "version": version, "admin_error": None}


def status_backend() -> dict:
    ok, data = _http_json("http://127.0.0.1:5001/health")
    if ok and isinstance(data, dict):
        return {"up": True, "health": data, "error": None}
    return {"up": False, "health": None, "error": str(data)}


def read_project_version() -> str:
    p = PROJECT_ROOT / "VERSION"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return "0.0.0"


def wiremock_jar_version() -> str | None:
    tools = PROJECT_ROOT / "tools"
    if not tools.is_dir():
        return None
    for f in sorted(tools.glob("wiremock-standalone-*.jar")):
        m = re.search(r"wiremock-standalone-([\d.]+)\.jar$", f.name)
        if m:
            return m.group(1)
    return None


def parse_compose_images() -> dict[str, str]:
    p = PROJECT_ROOT / "docker-compose.yml"
    if not p.is_file():
        return {}
    text = p.read_text(encoding="utf-8")
    images: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        svc = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
        if svc:
            current = svc.group(1)
            continue
        img = re.match(r"^\s+image:\s*(.+)\s*$", line)
        if img and current:
            images[current] = img.group(1).strip().strip('"').strip("'")
    return images


def read_backend_requirements_snippet() -> str:
    req = PROJECT_ROOT / "backend" / "requirements.txt"
    if not req.is_file():
        return ""
    lines = req.read_text(encoding="utf-8").strip().splitlines()
    return "\n".join(lines[:12])


def _win_creationflags() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return 0


def run_script_async(script: str) -> tuple[bool, str]:
    ps1 = PROJECT_ROOT / script
    if not ps1.is_file():
        return False, f"Missing script: {script}"
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
            ],
            cwd=str(PROJECT_ROOT),
            creationflags=_win_creationflags(),
        )
        return True, f"Launched {script}"
    except OSError as exc:
        return False, str(exc)


def run_script_wait(script: str, timeout: int = 120) -> tuple[bool, str]:
    ps1 = PROJECT_ROOT / script
    if not ps1.is_file():
        return False, f"Missing script: {script}"
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
            ],
            cwd=str(PROJECT_ROOT),
            creationflags=_win_creationflags(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return True, out.strip() or "OK"
        return False, out.strip() or f"Exit {proc.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Timed out"
    except OSError as exc:
        return False, str(exc)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("dashboard.html", port=MONITOR_PORT)

    @app.get("/api/overview")
    def overview():
        wm = status_wiremock()
        be = status_backend()
        return jsonify(
            {
                "project_version": read_project_version(),
                "wiremock_jar": wiremock_jar_version(),
                "compose_images": parse_compose_images(),
                "backend_requirements": read_backend_requirements_snippet(),
                "services": {
                    "wiremock": {
                        "label": "WireMock",
                        "port": 8080,
                        "up": wm["up"],
                        "version": wm.get("version"),
                        "admin_error": wm.get("admin_error"),
                    },
                    "backend": {
                        "label": "Customer API (Flask)",
                        "port": 5001,
                        "up": be["up"],
                        "health": be.get("health"),
                        "error": be.get("error"),
                    },
                },
            }
        )

    @app.post("/api/control/<action>")
    def control(action: str):
        mapping = {
            "start-backend": ("async", "start-backend.ps1"),
            "stop-backend": ("wait", "stop-backend.ps1"),
            "start-wiremock": ("async", "start-wiremock.ps1"),
            "stop-wiremock": ("wait", "stop-wiremock.ps1"),
            "start-all": ("async", "start-all.ps1"),
            "stop-all": ("wait", "stop-all.ps1"),
        }
        if action not in mapping:
            return jsonify({"ok": False, "message": "Unknown action"}), 400
        mode, script = mapping[action]
        if mode == "async":
            ok, msg = run_script_async(script)
        else:
            ok, msg = run_script_wait(script)
        return jsonify({"ok": ok, "message": msg, "action": action})

    @app.post("/api/docker/pull")
    def docker_pull():
        compose = PROJECT_ROOT / "docker-compose.yml"
        if not compose.is_file():
            return jsonify({"ok": False, "message": "No docker-compose.yml"}), 400
        try:
            proc = subprocess.run(
                ["docker", "compose", "-f", str(compose), "pull"],
                cwd=str(PROJECT_ROOT),
                creationflags=_win_creationflags(),
                capture_output=True,
                text=True,
                timeout=600,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode == 0:
                return jsonify({"ok": True, "message": out.strip() or "pull OK"})
            return jsonify({"ok": False, "message": out.strip() or "pull failed"}), 500
        except FileNotFoundError:
            return jsonify({"ok": False, "message": "docker not found"}), 500
        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "message": "docker compose pull timed out"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Monitor UI: http://127.0.0.1:{MONITOR_PORT}  (localhost only)")
    app.run(host="127.0.0.1", port=MONITOR_PORT, debug=False)
