"""
Interest Rates API: Returns static interest rates for different loan types.
WireMock reverse-proxies /rates* here.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request

APP_DIR = Path(__file__).resolve().parent

LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "rates.log"

logger = logging.getLogger("rates-api")
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


# Static interest rates by loan type
STATIC_RATES = {
    "home": 6.85,
    "auto": 5.45,
    "personal": 8.99,
    "student": 4.99,
    "business": 7.25,
}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/rates/quote", methods=["POST"])
    def get_rate_quote() -> tuple[dict, int]:
        if not request.is_json:
            logger.warning("Invalid request: Content-Type is not application/json")
            return {"error": "Content-Type must be application/json"}, 400

        body = request.get_json(silent=True) or {}
        loan_type = (body.get("loanType") or "").strip().lower()

        if not loan_type:
            logger.warning("Invalid request: missing loanType")
            return {"error": "Missing required field: loanType"}, 400

        if loan_type not in STATIC_RATES:
            logger.info("Rate lookup for unknown loan_type=%s", loan_type)
            return (
                {
                    "error": f"Unknown loan type: {loan_type}",
                    "available": list(STATIC_RATES.keys()),
                },
                404,
            )

        rate = STATIC_RATES[loan_type]
        logger.info("Rate quote for loan_type=%s rate=%.2f", loan_type, rate)

        return {
            "loanType": loan_type,
            "annualRate": rate,
            "message": "Static rate provided for demonstration",
        }, 200

    @app.route("/rates/all", methods=["POST"])
    def get_all_rates() -> dict:
        logger.info("All rates requested")
        return {
            "rates": [
                {"loanType": k, "annualRate": v} for k, v in STATIC_RATES.items()
            ]
        }

    @app.route("/health", methods=["GET"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5002"))
    app.run(host=host, port=port, debug=False)
