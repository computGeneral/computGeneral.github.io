# Unified self-hosted website

The Mac serves the public organization website and CGI through one domain. GitHub remains the content repository. Existing CGI clients can continue to use the previous endpoint during migration.

## Routing

- `/`: Jekyll website from `~/.computgeneral-site/current/site`.
- `/computing/intelligentia/`: separately exported CGI SPA, with Expo's web base path set to `/computing/intelligentia`.
- `/v1/`, `/v2/`, `/v3/`, `/files/`, `/socket.io/`: existing local CGI API, behind the existing gateway.
- `/_cgi-gateway/`: existing entry-password gateway. Its form returns to the requested CGI path.
- `/v1/updates`: Socket.IO connection, with CGI account-token verification, as with the existing deployment.

The API stays bound to `127.0.0.1:3006`, and the gateway to `127.0.0.1:3007`. The existing CGI services and their private state are not moved. A separate Caddy instance listens on 8445 and 8080. Router public 443 must forward to the Mac's 8445; public 80 must forward to 8080. The old CGI 5644→8444 forward remains available for compatibility.

## Build the website

Install Ruby 3.3 and the dependencies in `deploy/Gemfile`; commit its lockfile. Then run:

```sh
python3 deploy/publish-site.py
```

The publisher fetches `origin/main`, extracts only the selected Git commit to a temporary directory, builds with `deploy/overrides.yml`, checks the public routes, and atomically swaps the `current` symlink. It never checks out files into the working tree. Failed builds keep the prior site live. The publisher LaunchAgent checks once a minute, preserving the publish-on-GitHub workflow for blog articles.

## Build CGI for the nested path

From the website repository:

```sh
python3 deploy/publish-cgi.py --repo /absolute/path/to/cgi.computgeneral.com
```

It enforces CGI's release preflight: original checkout, clean `main`, matching a fresh `origin/main`. It builds a separate SPA, injects same-origin API configuration, verifies asset prefixes, commit metadata and absence of the old origin, then atomically updates `cgi-current`. It does not restart the CGI API or active agent sessions.

## Proxy service

Use a valid certificate covering `computgeneral.com` and `www.computgeneral.com`:

```sh
python3 deploy/install-services.py --cert /private/path/site.crt --key /private/path/site.key
```

Credentials and certificates live outside Git. Temporary self-signed certificates are only for explicit staging tests; never perform DNS cutover while staging TLS is in use. Proxy administration binds to loopback port 2020, separate from the legacy CGI Caddy admin endpoint.

## DNS and cutover

Before changing DNS, verify the new proxy using explicit host-to-IP resolution. The initial public IP must be obtained from the router, not from a proxy's synthetic DNS resolver. Preserve other records including mail, TXT and the old CGI hostname.

1. Obtain a valid certificate with DNS-01 while GitHub Pages stays online, or complete HTTP-01 after the public DNS and port 80 routing reach the new proxy.
2. Confirm the proxy has the valid certificate, main pages load, anonymous CGI/API requests are protected, entry-password login reaches CGI under the prefix, and refresh asks for the gateway password again.
3. Change the apex `@` A record to the current public IPv4. Change `www` CNAME from GitHub Pages to `computgeneral.com`. Set a short TTL during migration. Check/remove only conflicting apex or `www` AAAA records if no working IPv6 path is provided.
4. Run `python3 deploy/set-cgi-origin.py --repo /absolute/path/to/cgi.computgeneral.com` to update the API’s advertised attachment and webapp URLs. This restarts only the API after a clean-main preflight and rolls back if health checks fail. Existing agent processes, gateway passwords and account data are retained.
5. Verify both domains over public HTTPS; www redirects to the apex. Check CGI assets, API and Socket.IO traffic without the old hostname or port.
6. Update dynamic DNS for the apex A record, or arrange operator updates whenever the WAN IP changes. Do not assume a home WAN address is fixed.

## Certificate renewal

If using lego with HTTP-01, the `acme` directory is served at `/.well-known/acme-challenge/` over port 80. Renewal requires DNS still pointing to this server and the port 80 forward. The service installer adds `com.computgeneral.website-tls-renewal`, which runs `renew-tls.py` daily at 04:10. It renews via HTTP-01 when due and reloads only the website proxy when certificate bytes change. Check its logs after issuance. The legacy CGI certificate renewal is independent.

## Rollback

- Content: atomically point `current` to the directory referenced by `previous`.
- CGI frontend: restore `cgi-current` to its previously verified `cgi-releases/<commit>`.
- Public cutover: restore `www` CNAME to `computgeneral.github.io`, restore the prior apex records, and retain the GitHub Pages CNAME binding. The original GitHub Pages source config remains unchanged except exclusion of deployment tools.
- Proxy: service definitions and Caddyfile are backed up in the state directory before replacement. Never stop the existing CGI API, gateway or CLI daemons to roll back the website.
