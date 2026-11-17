#!/usr/bin/env python3
"""Build a Git revision and atomically publish it; never modify the user's checkout."""
import argparse, fcntl, json, os, pathlib, subprocess, tarfile, tempfile

def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def publish(repo, state, revision='origin/main'):
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'publish.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(['git', '-C', str(repo), 'fetch', 'origin', 'main'])
        sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', revision+'^{commit}'], text=True).strip()
        target = state / 'releases' / sha
        current = state / 'current'
        if current.is_symlink() and current.resolve() == target and (target / 'deployment.json').exists():
            print('UNCHANGED', sha)
            return
        target.mkdir(parents=True, exist_ok=True)
        # Extract only committed files, never private credentials or local changes.
        with tempfile.TemporaryDirectory(prefix='computgeneral-build-') as tmp:
            source = pathlib.Path(tmp).resolve() / 'source'; source.mkdir()
            archive = pathlib.Path(tmp) / 'source.tar'
            run(['git', '-C', str(repo), 'archive', '-o', str(archive), sha])
            with tarfile.open(archive) as tar:
                for member in tar.getmembers():
                    assert not member.issym() and not member.islnk(), 'Symlinks are not part of the deployable source'
                    assert source.resolve() in (source / member.name).resolve().parents, 'Unsafe archive path'
                tar.extractall(source)
            config = source / 'deploy/overrides.yml'
            gemfile = source / 'deploy/Gemfile'
            # Pin the installed deployment dependencies via the lockfile.
            env = os.environ.copy()
            env['BUNDLE_GEMFILE'] = str(gemfile)
            ruby_bin = env.get('COMPUTGENERAL_RUBY_BIN', '/opt/homebrew/opt/ruby@3.3/bin')
            env['PATH'] = ruby_bin + os.pathsep + env['PATH']
            run(['bundle', 'check'], cwd=source, env=env)
            run(['bundle', 'exec', 'jekyll', 'build', '--source', str(source), '--destination', str(target / 'site'), '--config', str(source / '_config.yml')+','+str(config)], cwd=source, env=env)
        home = (target / 'site/index.html').read_text()
        computing = (target / 'site/computing/index.html').read_text()
        assert 'General Computing' in home and 'General Rendering' in home
        assert 'Intelligentia entrance' not in home
        assert '/computing/intelligentia/' in computing
        assert 'lns.computgeneral.com' not in computing
        assert not (target / 'site/deploy').exists()
        assert not (target / 'site/oauth').exists()
        (target / 'deployment.json').write_text(json.dumps({'commit': sha}))
        previous = current.resolve() if current.is_symlink() else None
        if previous:
            link = state / 'previous.next'; link.unlink(missing_ok=True); link.symlink_to(previous); link.replace(state / 'previous')
        link = state / 'current.next'; link.unlink(missing_ok=True); link.symlink_to(target); link.replace(current)
        print('PUBLISHED', sha, 'previous:', str(previous))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--state', type=pathlib.Path, default=pathlib.Path.home()/'.computgeneral-site')
    parser.add_argument('--revision', default='origin/main')
    args=parser.parse_args()
    publish(args.repo.resolve(), args.state.resolve(), args.revision)
