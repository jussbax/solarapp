// Fills contact details and trust lines from the app's public profile, so they are edited in Settings, not in the pages.
(function () {
  var toggle = document.querySelector('.nav-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  var nav = document.body.getAttribute('data-page');
  document.querySelectorAll('[data-nav]').forEach(function (a) {
    if (a.getAttribute('data-nav') === nav) a.classList.add('on');
  });
  document.querySelectorAll('[data-year]').forEach(function (el) { el.textContent = String(new Date().getFullYear()); });

  function hrefFor(key, value) {
    if (key === 'phone') return 'tel:' + value.replace(/[^+\d]/g, '');
    if (key === 'email') return 'mailto:' + value;
    return value;
  }

  function apply(profile, warranty) {
    document.querySelectorAll('[data-profile]').forEach(function (el) {
      var v = profile[el.getAttribute('data-profile')];
      if (v) el.textContent = v;
    });
    document.querySelectorAll('[data-profile-href]').forEach(function (el) {
      var k = el.getAttribute('data-profile-href');
      var v = profile[k];
      if (v) el.setAttribute('href', hrefFor(k, v));
    });
    document.querySelectorAll('[data-profile-hide-if-empty]').forEach(function (el) {
      var v = profile[el.getAttribute('data-profile-hide-if-empty')];
      el.classList.toggle('is-empty', !v);
    });
    var anyContact = ['phone', 'messenger', 'facebook', 'email'].some(function (k) { return !!profile[k]; });
    document.querySelectorAll('[data-profile-empty-note]').forEach(function (el) { el.classList.toggle('is-hidden', anyContact); });
    var list = document.querySelector('[data-warranty-list]');
    if (list) {
      list.innerHTML = '';
      (warranty || []).forEach(function (w) {
        var li = document.createElement('li');
        li.textContent = w;
        list.appendChild(li);
      });
      var wrap = list.closest('[data-warranty-wrap]');
      if (wrap) wrap.classList.toggle('is-empty', !(warranty && warranty.length));
    }
  }

  try {
    fetch('/api/quick/status', { headers: { 'X-Visitor': 'site' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) { if (s && s.profile) apply(s.profile, s.warranty); })
      .catch(function () { /* the page stands on its own */ });
  } catch (e) { /* ignore */ }
})();
