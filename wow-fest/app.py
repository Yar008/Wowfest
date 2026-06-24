import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "registrations.db")
SEATS_PATH = os.path.join(DATA_DIR, "seats.json")

TOTAL_SEATS = 150  # измените под реальную вместимость площадки

GA4_MEASUREMENT_ID = os.environ.get("WOWFEST_GA4_ID", "")
FB_PIXEL_ID = os.environ.get("WOWFEST_FB_PIXEL_ID", "")


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest1_name TEXT NOT NULL,
            guest2_name TEXT,
            company TEXT,
            position TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            source TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    if not os.path.exists(SEATS_PATH):
        with open(SEATS_PATH, "w", encoding="utf-8") as f:
            json.dump({"total": TOTAL_SEATS, "taken": 0}, f)


def get_seats():
    with open(SEATS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def increment_seats():
    data = get_seats()
    data["taken"] += 1
    with open(SEATS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


@app.route("/")
def index():
    seats = get_seats()
    remaining = max(seats["total"] - seats["taken"], 0)
    return render_template(
        "index.html",
        remaining_seats=remaining,
        ga4_id=GA4_MEASUREMENT_ID,
        fb_pixel_id=FB_PIXEL_ID,
    )


@app.route("/api/seats")
def api_seats():
    seats = get_seats()
    remaining = max(seats["total"] - seats["taken"], 0)
    return jsonify({"remaining": remaining, "total": seats["total"]})


@app.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or request.form

    guest1_name = (payload.get("guest1_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    company = (payload.get("company") or "").strip()
    email = (payload.get("email") or "").strip()
    source = (payload.get("source") or "main_form").strip()

    if not guest1_name or not phone:
        return jsonify({"ok": False, "error": "Укажите имя и телефон"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO registrations
        (guest1_name, guest2_name, company, position, phone, email,
         source, utm_source, utm_medium, utm_campaign, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            guest1_name,
            (payload.get("guest2_name") or "").strip(),
            company,
            (payload.get("position") or "").strip(),
            phone,
            email,
            source,
            payload.get("utm_source") or "",
            payload.get("utm_medium") or "",
            payload.get("utm_campaign") or "",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    try:
        from sheets_integration import append_registration

        append_registration(payload)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Sheets sync failed: %s", exc)

    seats = increment_seats()
    remaining = max(seats["total"] - seats["taken"], 0)

    return jsonify({"ok": True, "remaining": remaining})


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
