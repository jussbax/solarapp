// Fills contact details and trust lines from the app's public profile, so they are edited in Settings, not in the pages.
(function () {
  var toggle = document.querySelector('.nav-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && document.body.classList.contains('nav-open')) {
        document.body.classList.remove('nav-open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
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
    // one key, or several separated by commas: hidden while every one of them is blank
    document.querySelectorAll('[data-profile-hide-if-empty]').forEach(function (el) {
      var keys = el.getAttribute('data-profile-hide-if-empty').split(',');
      var any = keys.some(function (k) { return !!profile[k.trim()]; });
      el.classList.toggle('is-empty', !any);
    });
    var list = document.querySelector('[data-warranty-list]');
    if (list) {
      list.innerHTML = '';
      (warranty || []).forEach(function (w) {
        var li = document.createElement('li');
        li.textContent = w;
        list.appendChild(li);
      });
    }
    // every warranty claim on the site stays hidden until the owner fills the years under Settings
    document.querySelectorAll('[data-warranty-wrap]').forEach(function (el) {
      var hidden = !(warranty && warranty.length);
      // a tile that also names its own key (the panel performance years) stays hidden while that key is blank
      if (el.hasAttribute('data-profile-hide-if-empty')) hidden = hidden || el.classList.contains('is-empty');
      el.classList.toggle('is-empty', hidden);
    });
  }

  try {
    fetch('/api/quick/status', { headers: { 'X-Visitor': 'site' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) { if (s && s.profile) apply(s.profile, s.warranty); })
      .catch(function () { /* the page stands on its own */ });
  } catch (e) { /* ignore */ }
})();
