#!/usr/bin/env python3
"""Verify staging proxy against a locally trusted test certificate; print no credentials."""
import hashlib, http.client, json, pathlib, re, socket, ssl, urllib.parse
state=pathlib.Path.home()/'.computgeneral-site'
context=ssl.create_default_context(cafile=str(state/'tls/staging.crt'))
class LocalHTTPS(http.client.HTTPSConnection):
    def connect(self):
        self.sock=context.wrap_socket(socket.create_connection(('127.0.0.1',8445),timeout=15),server_hostname='computgeneral.com')
def request(method,path,body=None,headers=None):
    connection=LocalHTTPS('computgeneral.com',8445,timeout=20)
    connection.request(method,path,body=body,headers=headers or {})
    response=connection.getresponse();data=response.read();result=response.status,dict(response.getheaders()),data
    connection.close();return result
for path in ['/','/computing/','/rendering/']:
    status,headers,body=request('GET',path)
    assert status==200 and b'lns.computgeneral.com' not in body
    if path=='/computing/':assert b'Intelligentia entrance' in body and b'/computing/intelligentia/' in body
print('Public pages and nested entry: PASS')
status,headers,body=request('GET','/computing/intelligentia/',headers={'Accept':'text/html'})
assert status==303 and headers['Location']=='/_cgi-gateway/login?next=%2Fcomputing%2Fintelligentia%2F'
assert request('GET','/v1/account/profile')[0]==401
print('Anonymous CGI and API protection: PASS')
password=(pathlib.Path.home()/'.cgi-server/gateway-password').read_text().strip()
form=urllib.parse.urlencode({'password':password,'next':'/computing/intelligentia/'})
status,headers,body=request('POST','/_cgi-gateway/login',form,{'Content-Type':'application/x-www-form-urlencoded'})
assert status==303 and headers['Location']=='/computing/intelligentia/'
cookie=headers['Set-Cookie'].split(';')[0]
status,headers,body=request('GET','/computing/intelligentia/',headers={'Accept':'text/html','Cookie':cookie})
assert status==200 and b'window.__CGI_CONFIG__' in body
scripts=re.findall(r'<script[^>]+src="([^"]+)"',body.decode())
assert scripts and all(x.startswith('/computing/intelligentia/') for x in scripts)
for script in scripts:
    status,headers,data=request('GET',script,headers={'Cookie':cookie})
    local=state/'cgi-current'/script.removeprefix('/computing/intelligentia/')
    assert status==200 and hashlib.sha256(data).digest()==hashlib.sha256(local.read_bytes()).digest()
print('Gateway login, same-origin config and script hashes: PASS')
token=json.loads((pathlib.Path.home()/'.cgi-client/access.key').read_text())['token']
assert request('GET','/v1/account/profile',headers={'Cookie':cookie,'Authorization':'Bearer '+token})[0]==200
assert request('GET','/computing/intelligentia/',headers={'Accept':'text/html','Cookie':cookie})[0]==303
print('Existing account token and gateway refresh protection: PASS')
assert request('GET','/deploy/Caddyfile')[0]==404
assert request('GET','/oauth/worker.mjs')[0]==404
print('Private deployment files excluded: PASS')
