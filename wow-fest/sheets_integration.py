"""
Интеграция с Google Sheets.

Есть два способа подключения — выберите тот, что удобнее.

────────────────────────────────────────────────────────────────────────
СПОСОБ 1 (рекомендуется, быстро — 10 минут): Google Apps Script Web App
────────────────────────────────────────────────────────────────────────
Не требует Google Cloud Console, service account и включения API.

1. Откройте вашу Google Таблицу.
2. Расширения → Apps Script.
3. Удалите содержимое редактора и вставьте код из файла apps_script.gs
   (лежит рядом с этим файлом — скопируйте его целиком).
4. Нажмите "Развернуть" → "Новое развертывание".
   - Тип: "Веб-приложение"
   - Кто имеет доступ: "Все"
5. Разрешите доступ (потребуется подтвердить от своего Google-аккаунта).
6. Скопируйте URL веб-приложения (вид https://script.google.com/macros/s/XXXX/exec).
7. Задайте переменную окружения:
   export WOWFEST_SHEETS_WEBHOOK_URL="https://script.google.com/macros/s/XXXX/exec"
   (в docker-compose.yml — впишите в environment, см. .env.example)
8. Готово — каждая заявка будет дописываться новой строкой в таблицу.

────────────────────────────────────────────────────────────────────────
СПОСОБ 2 (для продвинутых): Service Account + gspread
────────────────────────────────────────────────────────────────────────
1. Создайте Service Account в Google Cloud Console, включите Google Sheets API.
2. Скачайте JSON-ключ, сохраните как service_account.json в корне проекта
   (НЕ коммитьте в git — уже добавлено в .gitignore).
3. Откройте таблицу и дайте доступ email сервисного аккаунта (поле "client_email"
   в JSON) с правом редактора.
4. export WOWFEST_SPREADSHEET_ID="<ID таблицы из URL>"
5. pip install gspread google-auth
"""

import os
import requests

WEBHOOK_URL = os.environ.get("WOWFEST_SHEETS_WEBHOOK_URL", "")

SPREADSHEET_ID = os.environ.get("WOWFEST_SPREADSHEET_ID", "")
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "service_account.json")

_sheet = None


def append_registration(payload):
    """Отправляет одну заявку в Google Sheets. Пробует webhook, затем gspread."""
    if WEBHOOK_URL:
        _append_via_webhook(payload)
        return

    if SPREADSHEET_ID and os.path.exists(SERVICE_ACCOUNT_FILE):
        _append_via_gspread(payload)
        return

    raise RuntimeError(
        "Google Sheets не настроен: задайте WOWFEST_SHEETS_WEBHOOK_URL "
        "(способ 1, см. докстринг этого файла) или WOWFEST_SPREADSHEET_ID + "
        "service_account.json (способ 2)."
    )


def _row(payload):
    return [
        payload.get("guest1_name", ""),
        payload.get("guest2_name", ""),
        payload.get("company", ""),
        payload.get("position", ""),
        payload.get("phone", ""),
        payload.get("email", ""),
    ]


def _append_via_webhook(payload):
    resp = requests.post(WEBHOOK_URL, json={"row": _row(payload)}, timeout=8)
    resp.raise_for_status()


def _get_sheet():
    global _sheet
    if _sheet is not None:
        return _sheet

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    _sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return _sheet


def _append_via_gspread(payload):
    sheet = _get_sheet()
    sheet.append_row(_row(payload), value_input_option="USER_ENTERED")
