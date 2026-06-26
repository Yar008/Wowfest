import os
import re
import sqlite3
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _limiter_available = True
except ImportError:
    _limiter_available = False

app = Flask(__name__)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response


if _limiter_available:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://",
    )
    def _rate_limit(f):
        return limiter.limit("5 per minute; 20 per hour")(f)
else:
    app.logger.warning("Flask-Limiter not installed — rate limiting disabled")
    def _rate_limit(f):
        return f

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "registrations.db")

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
    # Счётчик мест в SQLite — атомарно, безопасно при нескольких воркерах
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seats_counter (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total INTEGER NOT NULL,
            taken INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO seats_counter (id, total, taken) VALUES (1, ?, 0)",
        (TOTAL_SEATS,),
    )
    conn.commit()
    conn.close()


def get_seats():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT total, taken FROM seats_counter WHERE id=1").fetchone()
    conn.close()
    return {"total": row[0], "taken": row[1]}


def increment_seats():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE seats_counter SET taken = taken + 1 WHERE id = 1"
    )
    conn.commit()
    row = conn.execute("SELECT total, taken FROM seats_counter WHERE id=1").fetchone()
    conn.close()
    return {"total": row[0], "taken": row[1]}


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
@_rate_limit
def register():
    payload = request.get_json(silent=True) or request.form

    guest1_name = (payload.get("guest1_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    company = (payload.get("company") or "").strip()
    email = (payload.get("email") or "").strip()
    source = (payload.get("source") or "main_form").strip()

    # Обязательные поля
    if not guest1_name or not phone:
        return jsonify({"ok": False, "error": "Укажите имя и телефон"}), 400

    # Ограничения длины (защита от DoS / переполнения)
    LIMITS = {"guest1_name": 100, "company": 200, "position": 100, "email": 254}
    for field, max_len in LIMITS.items():
        val = (payload.get(field) or "")
        if len(val) > max_len:
            return jsonify({"ok": False, "error": f"Поле '{field}' слишком длинное"}), 400

    # Телефон: только цифры после нормализации, 10–11 знаков
    phone_digits = re.sub(r"\D", "", phone)
    if not (10 <= len(phone_digits) <= 15):
        return jsonify({"ok": False, "error": "Неверный формат телефона"}), 400

    # Email: базовая проверка формата (если указан)
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"ok": False, "error": "Неверный формат e-mail"}), 400

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
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
