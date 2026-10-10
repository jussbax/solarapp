// Fills contact details and trust lines from the app's public profile, so they are edited in Settings, not in the pages;
// and the motion: sections come in as they scroll into view, the proof figures count up, the phone's sticky call to
// action appears after the hero. Nothing here is needed to read a page: with JavaScript off nothing is hidden.
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

  // ---- motion. Off entirely when the visitor asks for reduced motion or the browser has no IntersectionObserver.
  var motion = !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) && 'IntersectionObserver' in window;

  // Sections and cards below the fold come in as they scroll into view. Only what is not yet on screen is hidden,
  // so the first screen never flashes and nothing is hidden before this script runs.
  if (motion) {
    var below = [].filter.call(document.querySelectorAll('[data-reveal]'), function (el) {
      return el.getBoundingClientRect().top > window.innerHeight;
    });
    var byParent = {};
    below.forEach(function (el) {
      var p = el.parentNode;
      var key = p.__revealKey || (p.__revealKey = Math.random());
      var n = byParent[key] = (byParent[key] || 0) + 1;
      el.style.setProperty('--d', Math.min(n - 1, 5) * 0.08 + 's');
      el.classList.add('reveal');
    });
    var revealer = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); revealer.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -5% 0px' });
    below.forEach(function (el) { revealer.observe(el); });
  }

  // The proof figures count up once, when they come into view. The final text is the one written in the page.
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var prefix = el.getAttribute('data-prefix') || '';
    var suffix = el.getAttribute('data-suffix') || '';
    var done = el.textContent;
    var start = null, dur = 1400;
    function tick(now) {
      if (start === null) start = now;
      var t = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = t < 1 ? prefix + Math.round(target * eased).toLocaleString('en-US') + suffix : done;
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  if (motion) {
    var counter = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { countUp(e.target); counter.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-count]').forEach(function (el) { counter.observe(el); });
  }

  // The sticky call to action on the phone: after the hero has scrolled away, and never over the band or the footer,
  // which carry the button themselves.
  var hero = document.querySelector('.hero');
  var bar = document.querySelector('[data-sticky-cta]');
  if (hero && bar && 'IntersectionObserver' in window) {
    var pastHero = false, endInView = false, ends = document.querySelectorAll('.cta-band, .site-foot');
    var update = function () { document.documentElement.classList.toggle('cta-on', pastHero && !endInView); };
    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { pastHero = !e.isIntersecting && e.boundingClientRect.bottom < 0; });
      update();
    }, { threshold: 0 }).observe(hero);
    var endObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.target.__inView = e.isIntersecting; });
      endInView = [].some.call(ends, function (el) { return el.__inView; });
      update();
    }, { threshold: 0 });
    [].forEach.call(ends, function (el) { endObserver.observe(el); });
  }

  // The homes scroller on the phone: reachable from the keyboard when it overflows.
  var homes = document.querySelector('.homes');
  if (homes && homes.scrollWidth > homes.clientWidth + 8) {
    homes.setAttribute('tabindex', '0');
    homes.setAttribute('role', 'region');
  }
})();
