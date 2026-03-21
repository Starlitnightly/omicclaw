(function () {
  function getLanguageTarget(pathname) {
    if (pathname.indexOf('/en/') !== -1) {
      return {
        href: pathname.replace('/en/', '/zh/'),
        label: '中文',
        title: '切换为中文',
      };
    }

    if (pathname.indexOf('/zh/') !== -1) {
      return {
        href: pathname.replace('/zh/', '/en/'),
        label: 'EN',
        title: 'Switch to English',
      };
    }

    return null;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var target = getLanguageTarget(window.location.pathname);
    if (!target) return;

    var btn = document.createElement('a');
    btn.href = target.href;
    btn.className = 'lang-switch-btn';
    btn.title = target.title;
    btn.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="vertical-align:-2px;margin-right:4px"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>' +
      target.label;

    document.body.appendChild(btn);
  });
})();
