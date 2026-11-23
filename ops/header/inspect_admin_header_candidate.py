#!/usr/bin/env python3
"""Read-only diagnosis of the existing approved Admin header candidate.

Loads only the exact reviewed release helper; no deployment, cleanup or rebuild.
Prints field names, comparison results and fixed error codes, never values.
"""
from pathlib import Path
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True

def main():
    expected_hash = 'e48d7b22c86db69ceba167914f6d19d0405a81d30c846520ca93376e107bf01a'
    files = [p for p in Path('/root').glob('act-admin-header.*/admin_header_release.py')
             if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == expected_hash]
    if not files:
        raise RuntimeError()
    spec = importlib.util.spec_from_file_location('act_header_diagnostic', files[0])
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    prior = m.load_prior()
    r = m.Release(prior)
    p = m.RECORD
    saved = json.loads((p / 'pm2.before.json').read_bytes())
    before = [x for x in saved if x.get('pm_cwd') == str(m.ACTIVE)]
    if len(before) != 1:
        raise RuntimeError()
    r.current = {'name': before[0]['name'], 'pm2_env': before[0]}
    r.public = json.loads((p / 'public-environment.json').read_bytes())
    rows = r.rows()
    candidate = prior.one(rows, m.NAME)
    actual = candidate['pm2_env']
    wanted = r.candidate_config()

    def check(fn):
        try:
            result = fn()
            return True if result is None else result
        except m.Stop as error:
            return str(error)
        except Exception:
            return 'UNAVAILABLE'

    differences = {
        key: {'expected_type': type(value).__name__,
              'actual_type': type(actual.get('env', {}).get(key)).__name__}
        for key, value in wanted['env'].items()
        if actual.get('env', {}).get(key) != value
    }
    fields = {'pm_cwd': 'cwd', 'pm_exec_path': 'script',
              'exec_interpreter': 'interpreter', 'args': 'args'}
    plan = json.loads((p / 'plan.json').read_bytes())
    out = {
        'candidate_check': check(lambda: r.verify_candidate_row(candidate)),
        'candidate_launch_differences': [
            key for key, target in fields.items() if actual.get(key) != wanted[target]],
        'candidate_environment_differences': differences,
        'retained_launch_differences': {
            old['name']: check(lambda old=old: [
                key for key in prior.LAUNCH
                if prior.one(rows, old['name'])['pm2_env'].get(key) != old.get(key)])
            for old in saved},
        'active_public_configuration_unchanged': check(lambda:
            r.public_environment(prior.one(rows, before[0]['name'])) == r.public),
        'active_source_unchanged': check(lambda:
            m.source_tree(m.ACTIVE) == json.loads((p / 'source.before.json').read_bytes())),
        'backend_unchanged': check(lambda: r.backend() == plan['backend']),
        'pm2_start_reported_failure':
            b'Candidate startup refused or incomplete.' in (p / '05-pm2-start.log').read_bytes()
    }
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('READ_ONLY_DIAGNOSTIC_UNAVAILABLE; NO_CONFIGURATION_VALUES_PRINTED')
