"""
Отправка письма-подтверждения регистрации.

Настройка через переменные окружения (добавьте в .env):
  WOWFEST_SMTP_HOST=smtp.yandex.ru      # или smtp.gmail.com / smtp.mail.ru
  WOWFEST_SMTP_PORT=465                  # 465 для SSL, 587 для STARTTLS
  WOWFEST_SMTP_USER=your@yandex.ru      # логин (= адрес отправителя)
  WOWFEST_SMTP_PASS=your_app_password   # пароль приложения (не основной!)
  WOWFEST_SMTP_FROM=your@yandex.ru      # адрес «От кого» (обычно = USER)

Для Gmail нужен «Пароль приложения» (не основной пароль):
  Аккаунт Google → Безопасность → Двухэтапная аутентификация → Пароли приложений
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def _get_smtp_config():
    host = os.environ.get("WOWFEST_SMTP_HOST", "")
    port = int(os.environ.get("WOWFEST_SMTP_PORT", "465"))
    user = os.environ.get("WOWFEST_SMTP_USER", "")
    passwd = os.environ.get("WOWFEST_SMTP_PASS", "")
    from_addr = os.environ.get("WOWFEST_SMTP_FROM", user)
    return host, port, user, passwd, from_addr

SUBJECT = "Подтверждение регистрации — WOW! Ивент-Фест"

TEXT_BODY = """\
Добрый день, мы подтверждаем Вашу регистрацию на WOW ФЕСТ-ИВЕНТ.

Ждем Вас
14 июля в 15.30 в отеле Виктория Палас

До встречи на Первом корпоративном фестивале в Астрахани 💜
"""

HTML_BODY = """\
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0b0a1c;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#0b0a1c;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ec1e79;border-radius:20px;overflow:hidden;
                      max-width:560px;width:100%;">
          <!-- Header -->
          <tr>
            <td align="center" style="padding:36px 40px 28px;">
              <div style="font-family:Arial,sans-serif;font-size:28px;
                          font-weight:900;color:#f7c948;letter-spacing:-0.5px;">
                WOW<span style="color:#fff;">!</span>
              </div>
              <div style="font-size:10px;letter-spacing:3px;color:#fff;
                          text-transform:uppercase;margin-top:4px;">
                ИВЕНТ-ФЕСТ
              </div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:0 40px 40px;color:#ffffff;font-size:16px;
                       line-height:1.7;">
              <p style="margin:0 0 20px;">
                Добрый день,<br>
                мы подтверждаем Вашу регистрацию на <strong>WOW ФЕСТ-ИВЕНТ</strong>.
              </p>
              <table cellpadding="0" cellspacing="0"
                     style="background:rgba(0,0,0,.2);border-radius:14px;
                            width:100%;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;color:#fff;">
                    <div style="font-size:14px;opacity:.8;margin-bottom:6px;">
                      📅 Дата и время
                    </div>
                    <div style="font-size:20px;font-weight:700;color:#f7c948;">
                      14 июля в 15:30
                    </div>
                    <div style="font-size:14px;margin-top:8px;opacity:.9;">
                      📍 Отель <strong>Виктория Палас</strong>, Астрахань
                    </div>
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-size:16px;">
                До встречи на Первом корпоративном фестивале в Астрахани 💜
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td align="center"
                style="background:rgba(0,0,0,.25);padding:16px 40px;
                       font-size:12px;color:rgba(255,255,255,.6);">
              fest-event.ru
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_confirmation(to_email: str, guest_name: str) -> None:
    """Отправляет письмо-подтверждение на указанный адрес."""
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM = _get_smtp_config()

    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, to_email]):
        raise RuntimeError("SMTP не настроен или email не указан")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = f"WOW! Ивент-Фест <{SMTP_FROM}>"
    msg["To"] = to_email

    msg.attach(MIMEText(TEXT_BODY, "plain", "utf-8"))
    msg.attach(MIMEText(HTML_BODY, "html", "utf-8"))

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())

    logger.info("Confirmation email sent to %s", to_email)
