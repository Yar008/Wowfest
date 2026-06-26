/**
 * WOW! Ивент-Фест — приём заявок с лендинга в Google Таблицу.
 *
 * УСТАНОВКА:
 * 1. В Google Таблице: Расширения → Apps Script.
 * 2. Удалите весь код в редакторе, вставьте этот файл целиком.
 * 3. Сохраните (значок диска).
 * 4. Развернуть → Новое развертывание → тип "Веб-приложение".
 *    - Кто имеет доступ: "Все"
 * 5. Разрешить доступ от своего аккаунта (появится предупреждение
 *    "Google не проверял это приложение" — это нормально, это ваш
 *    собственный скрипт, нажмите "Дополнительно" → "Перейти на страницу...").
 * 6. Скопируйте URL веб-приложения и вставьте в переменную окружения
 *    WOWFEST_SHEETS_WEBHOOK_URL на стороне Flask-приложения.
 *
 * Если позже измените код скрипта — нужно создать НОВОЕ развертывание
 * (или "Управление развертываниями" → редактировать → новая версия),
 * иначе изменения не подхватятся.
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

    // При первом запуске добавим заголовки, если лист пустой
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        'Дата', 'Гость 1', 'Гость 2', 'Компания', 'Должность',
        'Телефон', 'E-mail'
      ]);
    }

    var data = JSON.parse(e.postData.contents);
    var row = data.row || [];

    // Телефон — индекс 4 в row (guest1, guest2, company, position, phone, email)
    // Убираем ведущий '+', чтобы Sheets не читал как формулу
    if (row[4] && typeof row[4] === 'string') {
      row[4] = row[4].replace(/^\+/, '');
    }

    sheet.appendRow([new Date()].concat(row));

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Удобно для проверки в браузере, что веб-приложение вообще отвечает
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, message: 'WOW Fest webhook работает' }))
    .setMimeType(ContentService.MimeType.JSON);
}
