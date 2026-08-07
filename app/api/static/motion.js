<script>
// Lâm Shop Admin — Motion Runtime
// Scroll reveal, active sidebar tracking, ripple effects
(function() {
  'use strict';

  // ── Scroll Reveal ────────────────────────────────────
  const revealObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(function(el) {
    revealObserver.observe(el);
  });

  // ── Active Sidebar Link ──────────────────────────────
  function updateActiveSidebar() {
    var sections = document.querySelectorAll('.admin-page');
    var links = document.querySelectorAll('.side-rail a[data-page-link]');
    var current = 'overview';

    sections.forEach(function(section) {
      if (section.classList.contains('active')) {
        current = section.id;
      }
    });

    links.forEach(function(link) {
      link.classList.remove('active');
      if (link.getAttribute('data-page-link') === current) {
        link.classList.add('active');
      }
    });
  }

  // Sidebar click handler
  document.querySelectorAll('.side-rail a[data-page-link]').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      var target = this.getAttribute('data-page-link');
      document.querySelectorAll('.admin-page').forEach(function(p) {
        p.classList.remove('active');
      });
      var targetEl = document.getElementById(target);
      if (targetEl) {
        targetEl.classList.add('active');
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      updateActiveSidebar();
    });
  });

  // Metric card click navigation
  document.querySelectorAll('.metric[data-page-link]').forEach(function(metric) {
    metric.addEventListener('click', function(e) {
      e.preventDefault();
      var target = this.getAttribute('data-page-link');
      document.querySelectorAll('.admin-page').forEach(function(p) {
        p.classList.remove('active');
      });
      var targetEl = document.getElementById(target);
      if (targetEl) {
        targetEl.classList.add('active');
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      updateActiveSidebar();
    });
  });

  // Quick action links
  document.querySelectorAll('.console-tools a[data-page-link]').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      var target = this.getAttribute('data-page-link');
      document.querySelectorAll('.admin-page').forEach(function(p) {
        p.classList.remove('active');
      });
      var targetEl = document.getElementById(target);
      if (targetEl) {
        targetEl.classList.add('active');
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      updateActiveSidebar();
    });
  });

  // ── Ripple Effect on Buttons ─────────────────────────
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('button, .btn, [role="button"]');
    if (!btn) return;
    var ripple = document.createElement('span');
    ripple.className = 'ripple-effect';
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    btn.appendChild(ripple);
    setTimeout(function() { ripple.remove(); }, 600);
  });

  // ── Global Search ────────────────────────────────────
  var searchInput = document.getElementById('globalSearch');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      var query = this.value.toLowerCase();
      var activePage = document.querySelector('.admin-page.active');
      if (!activePage) return;
      var rows = activePage.querySelectorAll('tbody tr');
      rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  }

  // ── Init ─────────────────────────────────────────────
  updateActiveSidebar();

  // Re-check on hash change
  window.addEventListener('hashchange', updateActiveSidebar);
})();
</script>
