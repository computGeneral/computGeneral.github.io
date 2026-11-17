#!/usr/bin/env python3
"""Switch the existing API's advertised public URLs after DNS cutover, with rollback."""
import argparse, json, os, pathlib, plistlib, subprocess, time, urllib.request
p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=pathlib.Path);p.add_argument('--state',type=pathlib.Path,default=pathlib.Path.home()/'.computgeneral-site');a=p.parse_args();repo=a.repo.resolve();state=a.state.resolve()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
subprocess.run(['git','-C',str(repo),'fetch','origin','main'],check=True)
assert git('branch','--show-current')=='main'
assert git('rev-parse','HEAD')==git('rev-parse','origin/main')
assert not git('status','--porcelain')
assert pathlib.Path(git('rev-parse','--path-format=absolute','--git-common-dir')).resolve()==repo/'.git'
file=pathlib.Path.home()/'Library/LaunchAgents/com.computgeneral.cgi-server.plist'
original=file.read_bytes();config=plistlib.loads(original)
backup=state/('cgi-server-before-origin-'+str(int(time.time()))+'.plist');backup.write_bytes(original);backup.chmod(0o600)
config['ProgramArguments'][0]=str(repo/'scripts/self-host/run-server.sh')
env=config.setdefault('EnvironmentVariables',{})
env.update({'CGI_SERVER_PORT':'3006','CGI_SERVER_DATA_DIR':str(pathlib.Path.home()/'.cgi-server'),'CGI_SERVER_PUBLIC_URL':'https://computgeneral.com','CGI_SERVER_WEBAPP_URL':'https://computgeneral.com/computing/intelligentia','CGI_INJECT_HTML_CONFIG':'{"serverUrl":"/","disableAnalytics":true}'})
domain='gui/'+str(os.getuid());service=domain+'/com.computgeneral.cgi-server'
def restart():
    subprocess.run(['launchctl','bootout',service],capture_output=True)
    for _ in range(80):
        if subprocess.run(['launchctl','print',service],capture_output=True).returncode!=0:break
        time.sleep(.1)
    else:raise RuntimeError('The previous API instance did not unload')
    subprocess.run(['launchctl','bootstrap',domain,str(file)],check=True)
    for _ in range(100):
        try:
            with urllib.request.urlopen('http://127.0.0.1:3006/health',timeout=2) as r:
                if r.status==200:return
        except Exception:time.sleep(.3)
    raise RuntimeError('API did not become ready')
file.write_bytes(plistlib.dumps(config))
try:restart()
except Exception:
    file.write_bytes(original);restart();raise
print('CGI public origin updated; API healthy. Existing account and session data preserved.')
