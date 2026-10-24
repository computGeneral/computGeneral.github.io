// Decap-compatible GitHub OAuth exchange. No token is stored on the server.
const REPOSITORY = 'computGeneral/computGeneral.github.io';
const COOKIE = '__Host-cg-oauth';
const headers = {
  'Cache-Control': 'no-store',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
};
const cookie = (value, age = 600) => `${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
const error = (status, message) => new Response(message, { status, headers });
const jsonForScript = value => JSON.stringify(value).replaceAll('<', '\\u003c');
function popup(origin, payload) {
  const nonce = crypto.randomUUID();
  const message = 'authorization:github:success:' + JSON.stringify(payload);
  return new Response(`<!doctype html><html lang="en"><meta charset="utf-8"><title>GitHub sign-in</title><p>Completing sign-in. You can close this window after returning to the editor.</p><script nonce="${nonce}">
const origin = ${jsonForScript(origin)};
const handler = event => {
  if (event.origin !== origin || event.source !== window.opener || event.data !== 'authorizing:github') return;
  window.removeEventListener('message', handler);
  window.opener.postMessage(${jsonForScript(message)}, origin);
  window.close();
};
window.addEventListener('message', handler);
if (window.opener) window.opener.postMessage('authorizing:github', origin);
</script></html>`, { headers: {
    ...headers, 'Content-Type': 'text/html; charset=utf-8',
    'Set-Cookie': cookie('', 0),
    'Content-Security-Policy': `default-src 'none'; script-src 'nonce-${nonce}'; frame-ancestors 'none'; base-uri 'none'`,
  } });
}
export async function handle(request, env, fetcher = fetch) {
  const url = new URL(request.url);
  if (request.method !== 'GET') return error(405, 'Method not allowed');
  if (url.pathname === '/health') return new Response('OK', { headers });
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET || !env.SITE_ORIGIN || !env.OAUTH_ORIGIN) {
    return error(503, 'OAuth is not configured.');
  }
  const origin = new URL(env.SITE_ORIGIN).origin;
  const oauthOrigin = new URL(env.OAUTH_ORIGIN).origin;
  if (url.origin !== oauthOrigin || !origin.startsWith('https://') || !oauthOrigin.startsWith('https://')) {
    return error(400, 'Invalid origin');
  }
  if (url.pathname === '/auth') {
    if (url.searchParams.get('provider') !== 'github' || url.searchParams.get('site_id') !== new URL(origin).hostname) {
      return error(400, 'Invalid provider or site');
    }
    const state = crypto.randomUUID();
    const authorize = new URL('https://github.com/login/oauth/authorize');
    authorize.search = new URLSearchParams({
      client_id: env.GITHUB_CLIENT_ID, redirect_uri: oauthOrigin + '/callback',
      scope: 'public_repo', state,
    }).toString();
    return new Response(null, { status: 302, headers: { ...headers, Location: authorize.href, 'Set-Cookie': cookie(state) } });
  }
  if (url.pathname !== '/callback') return error(404, 'Not found');
  const state = url.searchParams.get('state');
  const saved = request.headers.get('Cookie')?.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))?.slice(COOKIE.length + 1);
  if (!state || state !== saved || !/^[a-f0-9-]{36}$/.test(state)) return error(403, 'Invalid or expired sign-in. Return to the editor and try again.');
  const code = url.searchParams.get('code');
  if (!code || url.searchParams.has('error')) return error(400, 'GitHub sign-in was cancelled.');
  try {
    const response = await fetcher('https://github.com/login/oauth/access_token', {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code, redirect_uri: oauthOrigin + '/callback' }),
    });
    const token = await response.json();
    if (!response.ok || typeof token.access_token !== 'string') return error(401, 'GitHub did not authorize this sign-in.');
    const repository = await fetcher(`https://api.github.com/repos/${REPOSITORY}`, {
      headers: { Authorization: `Bearer ${token.access_token}`, Accept: 'application/vnd.github+json', 'User-Agent': 'ComputGeneral-Blog', 'X-GitHub-Api-Version': '2022-11-28' },
    });
    if (!repository.ok || !(await repository.json()).permissions?.push) return error(403, 'Your GitHub account needs write access to the website repository.');
    return popup(origin, { token: token.access_token, provider: 'github' });
  } catch {
    return error(502, 'GitHub is temporarily unavailable. Please try again.');
  }
}
export default { fetch(request, env) { return handle(request, env); } };
