document.addEventListener('DOMContentLoaded', function () {
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
