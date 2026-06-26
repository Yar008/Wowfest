/* ── Маска телефона +7 (XXX) XXX-XX-XX ── */
function applyPhoneMask(input) {
  input.addEventListener('input', function () {
    var digits = this.value.replace(/\D/g, '');
    // Всегда начинаем с 7
    if (digits.length === 0) { this.value = ''; return; }
    if (digits[0] === '8' || digits[0] === '7') digits = digits.slice(1);
    digits = digits.slice(0, 10);
    var mask = '+7';
    if (digits.length > 0) mask += ' (' + digits.slice(0, 3);
    if (digits.length >= 3) mask += ') ' + digits.slice(3, 6);
    if (digits.length >= 6) mask += '-' + digits.slice(6, 8);
    if (digits.length >= 8) mask += '-' + digits.slice(8, 10);
    this.value = mask;
  });

  // Не даём вводить нечисловые символы
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Backspace' || e.key === 'Delete' || e.key === 'Tab' ||
        e.key === 'ArrowLeft' || e.key === 'ArrowRight') return;
    if (!/\d/.test(e.key)) e.preventDefault();
  });

  // При фокусе — ставим +7 если пусто
  input.addEventListener('focus', function () {
    if (!this.value) this.value = '+7 ';
  });

  input.addEventListener('blur', function () {
    if (this.value === '+7 ' || this.value === '+7') this.value = '';
  });
}

/* Нормализация: '+7 (927) 282-38-57' → '79272823857' (без + и скобок — безопасно для Sheets) */
function normalizePhone(val) {
  return val.replace(/\D/g, '');
}

document.addEventListener('DOMContentLoaded', function () {
  // Применяем маску ко всем полям телефона
  document.querySelectorAll('input[name="phone"], input[type="tel"]').forEach(applyPhoneMask);
  // --- UTM capture ---
  var params = new URLSearchParams(window.location.search);
  var utmValues = {
    utm_source: params.get('utm_source') || '',
    utm_medium: params.get('utm_medium') || '',
    utm_campaign: params.get('utm_campaign') || '',
  };
  ['utm_source', 'utm_medium', 'utm_campaign'].forEach(function (key) {
    var el = document.getElementById(key);
    if (el) el.value = utmValues[key];
  });

  var seatsEl = document.getElementById('seats-remaining');

  function refreshSeats() {
    fetch('/api/seats')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (seatsEl) seatsEl.textContent = data.remaining;
      })
      .catch(function () {});
  }
  refreshSeats();

  function submitLead(form, statusEl, onSuccess) {
    var data = {};
    new FormData(form).forEach(function (value, key) { data[key] = value; });
    // Нормализуем телефон: оставляем только цифры → '79272823857'
    // Sheets не интерпретирует числовую строку без спецсимволов как формулу
    if (data.phone) data.phone = normalizePhone(data.phone);

    statusEl.textContent = 'Отправляем...';
    statusEl.className = 'form-status';

    return fetch('/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
      .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
      .then(function (result) {
        if (result.ok && result.body.ok) {
          statusEl.textContent = 'Готово! Мы отправили приглашение на e-mail / телефон.';
          statusEl.className = 'form-status success';
          form.reset();
          if (seatsEl && typeof result.body.remaining === 'number') {
            seatsEl.textContent = result.body.remaining;
          }
          if (window.fbq) fbq('track', 'Lead');
          if (window.gtag) gtag('event', 'generate_lead');
          if (onSuccess) onSuccess();
        } else {
          statusEl.textContent = result.body.error || 'Что-то пошло не так. Проверьте поля.';
          statusEl.className = 'form-status error';
        }
      })
      .catch(function () {
        statusEl.textContent = 'Ошибка соединения. Попробуйте ещё раз.';
        statusEl.className = 'form-status error';
      });
  }

  // --- Main registration form ---
  var form = document.getElementById('register-form');
  var status = document.getElementById('form-status');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      submitLead(form, status);
    });
  }
});
