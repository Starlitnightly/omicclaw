(function () {
  function getDirectChild(parent, selector) {
    for (var i = 0; i < parent.children.length; i += 1) {
      if (parent.children[i].matches(selector)) {
        return parent.children[i];
      }
    }
    return null;
  }

  function initSidebarToggles() {
    var items = document.querySelectorAll('.bd-sidenav li.has-children');

    items.forEach(function (item) {
      var childList = getDirectChild(item, 'ul');
      var details = getDirectChild(item, 'details');
      if (!childList || !details) return;

      var summary = getDirectChild(details, 'summary');
      var anchor = getDirectChild(item, 'a');
      var key = 'omicclaw-sidebar:' + (anchor ? anchor.getAttribute('href') : item.textContent.trim());

      function applyState(open) {
        childList.hidden = !open;
        item.classList.toggle('is-collapsed', !open);
        if (summary) {
          summary.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
      }

      try {
        var saved = window.sessionStorage.getItem(key);
        if (saved === 'open') details.open = true;
        if (saved === 'closed') details.open = false;
      } catch (error) {
        // Ignore storage failures and continue with document defaults.
      }

      applyState(details.open);

      details.addEventListener('toggle', function () {
        applyState(details.open);
        try {
          window.sessionStorage.setItem(key, details.open ? 'open' : 'closed');
        } catch (error) {
          // Ignore storage failures.
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', initSidebarToggles);
})();
