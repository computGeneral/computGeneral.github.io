import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../oauth/worker.mjs';
const env = { GITHUB_CLIENT_ID: 'test-client', GITHUB_CLIENT_SECRET: 'server-secret', SITE_ORIGIN: 'https://www.computgeneral.com', OAUTH_ORIGIN: 'https://blog-auth.computgeneral.com' };
const state = '01234567-1234-1234-1234-012345678901';
const request = (path, options) => new Request(env.OAUTH_ORIGIN + path, options);
const callback = () => request('/callback?state=' + state + '&code=code', { headers: { Cookie: '__Host-cg-oauth=' + state } });
test('requires configured secrets and rejects unrelated sites', async () => {
  assert.equal((await handle(request('/auth'), {})).status, 503);
  assert.equal((await handle(request('/auth?provider=github&site_id=attacker.example'), env)).status, 400);
});
test('authorization requests use fixed public repo scope and protected state cookie', async () => {
  const r = await handle(request('/auth?provider=github&site_id=www.computgeneral.com&scope=repo'), env);
  assert.equal(r.status, 302);
  const url = new URL(r.headers.get('Location'));
  assert.equal(url.searchParams.get('scope'), 'public_repo');
  assert.equal(url.searchParams.get('redirect_uri'), env.OAUTH_ORIGIN + '/callback');
  assert.match(r.headers.get('Set-Cookie'), /HttpOnly; Secure; SameSite=Lax/);
  assert.ok(!r.headers.get('Location').includes('server-secret'));
});
test('rejects callback without matching browser state before any exchange', async () => {
  const r = await handle(request('/callback?state=' + state + '&code=code'), env, () => { throw new Error('must not fetch'); });
  assert.equal(r.status, 403);
});
test('denies repository readers', async () => {
  let n = 0;
  const r = await handle(callback(), env, async () => Response.json(++n === 1 ? { access_token: 'reader-token' } : { permissions: { push: false } }));
  assert.equal(r.status, 403);
  assert.ok(!(await r.text()).includes('reader-token'));
});
test('only returns writer token to exact trusted opener with no executable injection', async () => {
  let n = 0;
  const r = await handle(callback(), env, async () => Response.json(++n === 1 ? { access_token: '</script><script>bad()</script>' } : { permissions: { push: true } }));
  assert.equal(r.status, 200);
  const html = await r.text();
  assert.ok(html.includes("event.source !== window.opener"));
  assert.ok(html.includes('https://www.computgeneral.com'));
  assert.ok(!html.includes('</script><script>bad()'));
  assert.ok(!html.includes(env.GITHUB_CLIENT_SECRET));
  assert.match(r.headers.get('Content-Security-Policy'), /frame-ancestors 'none'/);
  assert.match(r.headers.get('Set-Cookie'), /Max-Age=0/);
});
test('GitHub network failure does not expose secrets', async () => {
  const r = await handle(callback(), env, async () => { throw Error(env.GITHUB_CLIENT_SECRET); });
  assert.equal(r.status, 502);
  assert.ok(!(await r.text()).includes(env.GITHUB_CLIENT_SECRET));
});
