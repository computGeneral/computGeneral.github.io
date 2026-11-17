#!/usr/bin/env python3
"""Install the separate website proxy and Git-driven static publisher on this Mac."""
import argparse, os, pathlib, plistlib, shutil, subprocess, time

def install(repo, state, cert, key):
    assert (state/'current/site/index.html').is_file(), 'Publish the website first'
    assert (state/'cgi-current/index.html').is_file(), 'Publish prefixed CGI first'
    assert cert.is_file() and key.is_file(), 'Provide certificate and key paths'
    state.mkdir(parents=True,exist_ok=True)
    env={'COMPUTGENERAL_STATE_DIR':str(state),'COMPUTGENERAL_TLS_CERT':str(cert),'COMPUTGENERAL_TLS_KEY':str(key),'PATH':'/opt/homebrew/bin:/usr/bin:/bin'}
    config=state/'Caddyfile'
    if config.exists():shutil.copyfile(config,state/('Caddyfile.backup-'+str(int(time.time()))))
    shutil.copyfile(repo/'deploy/Caddyfile',config)
    subprocess.run(['/opt/homebrew/bin/caddy','validate','--config',str(config),'--adapter','caddyfile'],env={**os.environ,**env},check=True)
    directory=pathlib.Path.home()/'Library/LaunchAgents';directory.mkdir(parents=True,exist_ok=True)
    agents=[
      {'Label':'com.computgeneral.website-proxy','ProgramArguments':['/opt/homebrew/bin/caddy','run','--config',str(config),'--adapter','caddyfile'],'KeepAlive':True,'RunAtLoad':True,'EnvironmentVariables':env},
      {'Label':'com.computgeneral.website-publisher','ProgramArguments':['/usr/bin/python3',str(repo/'deploy/publish-site.py'),'--repo',str(repo),'--state',str(state)],'RunAtLoad':True,'StartInterval':60,'EnvironmentVariables':{'PATH':'/opt/homebrew/bin:/usr/bin:/bin','GIT_SSH_COMMAND':'ssh -o BatchMode=yes -o ConnectTimeout=10'}},
    ]
    domain='gui/'+str(os.getuid())
    for agent in agents:
        label=agent['Label'];file=directory/(label+'.plist')
        agent.update({'StandardOutPath':str(state/(label+'.log')),'StandardErrorPath':str(state/(label+'.error.log')),'WorkingDirectory':str(repo)})
        if file.exists():shutil.copyfile(file,state/(label+'.backup-'+str(int(time.time()))+'.plist'))
        file.write_bytes(plistlib.dumps(agent));file.chmod(0o600)
        subprocess.run(['launchctl','bootout',domain+'/'+label],capture_output=True)
        subprocess.run(['launchctl','bootstrap',domain,str(file)],check=True)
        print('INSTALLED',label)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);p.add_argument('--state',type=pathlib.Path,default=pathlib.Path.home()/'.computgeneral-site');p.add_argument('--cert',required=True,type=pathlib.Path);p.add_argument('--key',required=True,type=pathlib.Path)
    a=p.parse_args();install(a.repo.resolve(),a.state.resolve(),a.cert.resolve(),a.key.resolve())
