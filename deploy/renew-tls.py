#!/usr/bin/env python3
"""Renew the main site's certificate with HTTP-01; never print private material."""
import argparse, hashlib, os, pathlib, plistlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--state',type=pathlib.Path,default=pathlib.Path.home()/'.computgeneral-site');a=p.parse_args()
state=a.state.resolve();tls=state/'tls';certificate=tls/'certificates/computgeneral.com.crt'
if not certificate.exists():
    print('No production certificate installed yet; renewal skipped.')
    raise SystemExit(0)
accounts=list((tls/'accounts/acme-v02.api.letsencrypt.org').iterdir())
accounts=[x for x in accounts if x.is_dir()]
assert len(accounts)==1, 'Select the ACME account explicitly'
before=hashlib.sha256(certificate.read_bytes()).digest()
subprocess.run(['/opt/homebrew/bin/lego','run','--email',accounts[0].name,'--accept-tos','--domains','computgeneral.com','--domains','www.computgeneral.com','--path',str(tls),'--http','--http.webroot',str(state/'acme'),'--renew-days','30'],check=True)
after=hashlib.sha256(certificate.read_bytes()).digest()
if before != after:
    service=plistlib.loads((pathlib.Path.home()/'Library/LaunchAgents/com.computgeneral.website-proxy.plist').read_bytes())
    env={**os.environ,**service['EnvironmentVariables']}
    subprocess.run(['/opt/homebrew/bin/caddy','reload','--address','127.0.0.1:2020','--config',str(state/'Caddyfile'),'--adapter','caddyfile'],env=env,check=True)
    print('Renewed certificate and reloaded the website proxy.')
else:
    print('Certificate is not due for renewal.')
