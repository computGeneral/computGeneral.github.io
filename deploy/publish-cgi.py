#!/usr/bin/env python3
"""Export the CGI SPA at its nested URL without restarting the existing CGI API."""
import argparse, hashlib, json, os, pathlib, re, subprocess

def output(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def publish(repo, state):
    repo=repo.resolve(); state=state.resolve()
    subprocess.run(['git', '-C', str(repo), 'fetch', 'origin', 'main'], check=True)
    assert output(repo,'branch','--show-current')=='main', 'CGI requires main'
    sha=output(repo,'rev-parse','HEAD')
    assert sha==output(repo,'rev-parse','origin/main'), 'CGI main must match freshly fetched origin/main'
    assert not output(repo,'status','--porcelain'), 'CGI requires a clean tree'
    common=pathlib.Path(output(repo,'rev-parse','--path-format=absolute','--git-common-dir')).resolve()
    assert common==repo/'.git', 'Do not release CGI from a worktree'
    target=state/'cgi-releases'/sha
    target.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    runtime=repo/'__install__/bin/runtime/node/bin'
    env['PATH']=str(runtime)+os.pathsep+env['PATH']
    env.update({'CGI_WEB_BASE_PATH':'/computing/intelligentia','EXPO_PUBLIC_CGI_SERVER_URL':'https://computgeneral.com','CGI_BUILD_COMMIT_SHA':sha,'APP_ENV':'production'})
    subprocess.run(['pnpm','exec','expo','export','-p','web','--clear','--output-dir',str(target)],cwd=repo/'packages/cgi-app',env=env,check=True)
    assert not output(repo,'status','--porcelain'), 'Build modified tracked CGI files'
    index=target/'index.html'
    html=index.read_text()
    scripts=re.findall(r'<script[^>]+src="([^"]+)"',html)
    assert scripts and all(x.startswith('/computing/intelligentia/') for x in scripts), 'Wrong asset prefix'
    injected='<script>window.__CGI_CONFIG__ = window.__HAPPY_CONFIG__ = {"serverUrl":"/","disableAnalytics":true};</script>'
    index.write_text(html.replace('<head>','<head>'+injected,1))
    assert injected in index.read_text(), 'Runtime config injection failed'
    all_js=list((target/'_expo/static/js').rglob('*.js'))
    assert any(sha in x.read_text() for x in all_js), 'Build metadata does not match source commit'
    assert not any('lns.computgeneral.com' in x.read_text() for x in all_js), 'Old origin leaked into prefixed app bundle'
    (target/'deployment.json').write_text(json.dumps({'commit':sha,'basePath':'/computing/intelligentia','scripts':scripts}))
    link=state/'cgi-current.next'; link.unlink(missing_ok=True); link.symlink_to(target); link.replace(state/'cgi-current')
    print('CGI_PREFIX_PUBLISHED',sha)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=pathlib.Path);p.add_argument('--state',type=pathlib.Path,default=pathlib.Path.home()/'.computgeneral-site')
    args=p.parse_args();publish(args.repo,args.state)
