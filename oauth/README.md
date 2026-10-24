# GitHub login setup

The public blogs and GitHub web-editor fallback work without this service. The embedded Decap editor requires one GitHub OAuth App and a deployed authenticator. `admin/settings.json` intentionally disables it until setup is verified.

## Deploy the authenticator

The included `worker.mjs` implements Decap's popup OAuth protocol on Cloudflare Workers, separate from CGI. This project does not require changing the CGI server or its login.

1. Deploy from this directory using `npx wrangler deploy` after authenticating to your Cloudflare account. Review any account plan or routing choices in Cloudflare before deploying.
2. Add `blog-auth.computgeneral.com` as the Worker's custom domain. This requires DNS management for the domain in Cloudflare. Alternatively use the assigned `workers.dev` hostname and update `OAUTH_ORIGIN` in `wrangler.toml` and `backend.base_url` in `admin/config.yml` to match.
3. Register an OAuth App at <https://github.com/settings/applications/new>:
   - Application name: `ComputGeneral Blog`
   - Homepage URL: `https://www.computgeneral.com`
   - Authorization callback URL: `https://blog-auth.computgeneral.com/callback` (use the actual Worker hostname if different).
4. Store the credentials using prompts; never commit or paste secrets into chat:

   ```sh
   npx wrangler secret put GITHUB_CLIENT_ID
   npx wrangler secret put GITHUB_CLIENT_SECRET
   ```

5. Verify `https://blog-auth.computgeneral.com/health` returns `OK`, then set `oauth_enabled` to `true` in `admin/settings.json` and publish the site.
6. Open `/computing/`, select **New post**, sign in with a repository writer, publish a temporary post, verify it appears after Pages deployment, edit it, and remove it. Repeat for Rendering. Revoke the test authorization if appropriate.

## Permissions and content

The OAuth client requests `public_repo` because this site is a public repository. GitHub OAuth scopes are not limited to one repository; GitHub's authorization screen lists the requested access. Only accounts with push access to `computGeneral/computGeneral.github.io` receive a CMS token. There is no open registration or reader publishing.

The client secret stays in Worker secrets. The token exchange occurs on the Worker, and Decap receives the user's access token through an exact-origin popup handshake. Decap manages its browser session; sign out when finished on a shared device. No token or secret is written into posts, static site configuration or URL query parameters.

The GitHub web-editor fallback commits Markdown directly to `_computing/` or `_rendering/`. The regular Pages deployment then publishes the article. All committed content and uploaded images are public; do not use this public repository for private drafts.

Run authenticator tests from the repository root:

```sh
node --test tests/oauth.test.mjs
```

References: [Decap GitHub backend](https://decapcms.org/docs/github-backend/), [GitHub OAuth web flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps).
