/* GitHub OAuth is enabled only after the owner deploys the authenticator. */
(async function () {
  const status = document.getElementById('editor-status');
  function updateFallback() {
    const category = location.hash.includes('/rendering') ? 'rendering' : 'computing';
    const entry = location.hash.match(/\/entries\/([^/]+)$/);
    let fallback;
    if (entry) {
      fallback = new URL('https://github.com/computGeneral/computGeneral.github.io/edit/main/_' + category + '/' + encodeURIComponent(decodeURIComponent(entry[1])) + '.md');
    } else {
      const frontmatter = '---\ntitle: Untitled\ndate: ' + new Date().toISOString() + '\ndescription: ""\n---\n\nWrite your post here.\n';
      fallback = new URL('https://github.com/computGeneral/computGeneral.github.io/new/main/_' + category);
      fallback.searchParams.set('filename', new Date().toISOString().slice(0, 10) + '-new-post.md');
      fallback.searchParams.set('value', frontmatter);
    }
    const link = document.getElementById('github-create');
    link.href = fallback.href;
    link.textContent = entry ? 'Edit on GitHub ↗' : 'Write on GitHub ↗';
  }
  updateFallback();
  window.addEventListener('hashchange', updateFallback);
  try {
    const settings = await fetch('/admin/settings.json').then(r => { if (!r.ok) throw new Error(); return r.json(); });
    if (!settings.oauth_enabled) {
      status.textContent = 'Editor setup';
      document.getElementById('editor-help').hidden = false;
      return;
    }
    if (!window.CMS) throw new Error('Editor unavailable');
    window.CMS.init();
    window.CMS.registerPreviewStyle('/assets/css/style.css');
    status.remove();
  } catch (error) {
    status.textContent = 'The editor could not load. Please try again.';
    document.getElementById('editor-help').hidden = false;
  }
})();
