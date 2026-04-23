"""
Loan Application API: Manage loan applications.
WireMock reverse-proxies /loans* here.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request

APP_DIR = Path(__file__).resolve().parent

LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "loans.log"

logger = logging.getLogger("loans-api")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# In-memory storage for loan applications (in production, use a database)
_applications = {}
_lock = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/loans/apply", methods=["POST"])
    def apply_for_loan() -> tuple[dict, int]:
        if not request.is_json:
            logger.warning("Invalid request: Content-Type is not application/json")
            return {"error": "Content-Type must be application/json"}, 400

        body = request.get_json(silent=True) or {}
        customer_id = (body.get("customerId") or "").strip()
        loan_type = (body.get("loanType") or "").strip()
        amount = body.get("loanAmount")

        # Validation
        if not customer_id or not loan_type or amount is None:
            logger.warning("Invalid request: missing required fields")
            return (
                {
                    "error": "Missing required fields: customerId, loanType, loanAmount"
                },
                400,
            )

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            logger.warning("Invalid amount: %s", amount)
            return {"error": "loanAmount must be a positive number"}, 400

        # Create application
        app_id = f"loan-{uuid.uuid4().hex[:8]}"
        application = {
            "applicationId": app_id,
            "customerId": customer_id,
            "loanType": loan_type,
            "loanAmount": amount,
            "status": "PENDING",
            "createdAt": _utc_now_iso(),
            "approvalDate": None,
        }

        with _lock:
            _applications[app_id] = application

        logger.info(
            "Loan application created: app_id=%s customer_id=%s loan_type=%s amount=%.2f",
            app_id,
            customer_id,
            loan_type,
            amount,
        )

        return {
            "applicationId": app_id,
            "status": "PENDING",
            "message": "Loan application submitted successfully",
        }, 201

    @app.route("/loans/<application_id>", methods=["GET"])
    def get_application(application_id: str) -> tuple[dict, int]:
        with _lock:
            app = _applications.get(application_id)

        if not app:
            logger.info("Application not found: app_id=%s", application_id)
            return {"error": "Application not found"}, 404

        logger.info(
            "Application retrieved: app_id=%s status=%s", application_id, app["status"]
        )
        return app, 200

    @app.route("/loans/<application_id>/approve", methods=["POST"])
    def approve_application(application_id: str) -> tuple[dict, int]:
        with _lock:
            app = _applications.get(application_id)

        if not app:
            logger.info("Approval failed: application not found: app_id=%s", application_id)
            return {"error": "Application not found"}, 404

        if app["status"] == "APPROVED":
            logger.info("Application already approved: app_id=%s", application_id)
            return {"error": "Application already approved"}, 409

        with _lock:
            app["status"] = "APPROVED"
            app["approvalDate"] = _utc_now_iso()

        logger.info("Application approved: app_id=%s", application_id)
        return {
            "applicationId": application_id,
            "status": "APPROVED",
            "message": "Loan application approved",
        }, 200

    @app.route("/loans/<application_id>/reject", methods=["POST"])
    def reject_application(application_id: str) -> tuple[dict, int]:
        body = request.get_json(silent=True) or {}
        reason = (body.get("reason") or "").strip()

        with _lock:
            app = _applications.get(application_id)

        if not app:
            logger.info("Rejection failed: application not found: app_id=%s", application_id)
            return {"error": "Application not found"}, 404

        if app["status"] in ("APPROVED", "REJECTED"):
            logger.info(
                "Cannot reject: application status=%s app_id=%s",
                app["status"],
                application_id,
            )
            return (
                {"error": f"Cannot reject application with status {app['status']}"},
                409,
            )

        with _lock:
            app["status"] = "REJECTED"
            app["rejectionReason"] = reason or "No reason provided"

        logger.info("Application rejected: app_id=%s reason=%s", application_id, reason)
        return {
            "applicationId": application_id,
            "status": "REJECTED",
            "message": "Loan application rejected",
        }, 200

    @app.route("/loans/applications", methods=["GET"])
    def list_applications() -> dict:
        with _lock:
            apps = list(_applications.values())
        logger.info("Listed all applications: count=%d", len(apps))
        return {"applications": apps}

    @app.route("/health", methods=["GET"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5003"))
    app.run(host=host, port=port, debug=False)
