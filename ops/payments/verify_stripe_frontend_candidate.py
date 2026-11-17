#!/usr/bin/env python3
"""Read-only post-build acceptance gate for ACT's inactive frontend test-key repair.

Prints fixed, nonsecret statuses only. No Stripe API, payment, filesystem write,
PM2, systemd or Nginx mutation. Requires original pinned staging helper locally.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

HELPER_FILE = Path('/root/act-stripe-readonly/prepare_stripe_frontend_candidate.py')
HELPER_SHA256 = 'cd94c5e9dbcd186a2a8bc7ea6a60d8724f4c604214c4eac8a5e084edb37807bf'
FRONT_SHA = '02e59f95b5fd85d6ad07e881f3f2671a01a7bd65'
BACK_SHA = 'd77e896af9daca5a39b7a85d5b76c5821e008d23'
SOURCE_PATHS = (
    'src/components/_components/stripe/CheckoutForm.tsx',
    'src/components/_components/stripe/StripeWrapper.tsx',
    'src/components/_components/bookTaxi/PaymentDsetails.tsx',
    'src/components/_components/bookTaxi/ConfirmFlightDetails.tsx',
    'src/components/_components/bookTaxi/index.tsx',
    'src/components/_components/Trips/MyTripsCard.tsx',
    'src/hooks/use-trip-tracking.ts',
    'src/lib/customer-runtime.ts',
)

class Stop(Exception):
    """Must contain a fixed, safe status code only."""

def require(condition, code):
    if not condition:
        raise Stop(code)

def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()

def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            chunk = stream.read(131072)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

def import_pinned_helper():
    require(HELPER_FILE.is_file() and not HELPER_FILE.is_symlink(), 'PINNED_STAGING_HELPER_MISSING')
    require(hash_file(HELPER_FILE) == HELPER_SHA256, 'PINNED_STAGING_HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location('act_frontend_stage_checked', HELPER_FILE)
    require(spec is not None and spec.loader is not None, 'PINNED_HELPER_IMPORT_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def private_plan(path):
    require(not path.is_symlink(), 'PLAN_LINK_NOT_ALLOWED')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == 0
            and not stat.S_IMODE(info.st_mode) & 0o077 and 0 < info.st_size < 65536,
            'PLAN_NOT_PRIVATE_OR_INVALID')
    folder = path.parent.stat()
    require(not path.parent.is_symlink() and folder.st_uid == 0
            and stat.S_ISDIR(folder.st_mode) and not stat.S_IMODE(folder.st_mode) & 0o077,
            'PLAN_DIRECTORY_NOT_PRIVATE')
    plan = json.loads(path.read_bytes())
    require(isinstance(plan, dict), 'PLAN_INVALID_JSON_STRUCTURE')
    return plan

def validate_plan(stage, plan, baseline):
    expected = {
        'status':'PREPARED_NOT_ACTIVATED', 'source_sha':FRONT_SHA,
        'backend_sha':BACK_SHA, 'old_build_id':baseline['active_build_id'],
        'candidate':str(stage.CANDIDATE), 'candidate_assets':str(stage.NEW_ASSETS),
        'old_release':str(stage.ACTIVE), 'old_assets':str(stage.OLD_ASSETS),
        'nginx_sha256':baseline['nginx_sha256'],
        'backend_env_sha256':baseline['backend_env_sha256'],
        'old_public_key_sha256':hash_bytes(baseline['active_public']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'].encode()),
        'activation_authorized':False, 'webhook_changed':False,
        'backend_changed':False, 'current_frontend_changed':False,
    }
    for name, value in expected.items():
        require(plan.get(name) == value, 'PLAN_BASELINE_MISMATCH')
    require(not isinstance(plan.get('new_build_id'), bool) and
            isinstance(plan.get('new_build_id'), str) and
            re.fullmatch(r'[A-Za-z0-9_-]{1,128}', plan['new_build_id']) is not None,
            'CANDIDATE_BUILD_ID_INVALID')
    require(isinstance(plan.get('new_public_key_sha256'), str) and
            re.fullmatch(r'[0-9a-f]{64}', plan['new_public_key_sha256']) is not None and
            plan['new_public_key_sha256'] != plan['old_public_key_sha256'],
            'NEW_KEY_FINGERPRINT_INVALID')

def directory_map(root):
    require(root.is_dir() and not root.is_symlink(), 'ASSET_DIRECTORY_UNAVAILABLE')
    found={}
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'ASSET_LINK_NOT_ALLOWED')
        if path.is_dir():
            continue
        require(path.is_file(), 'ASSET_NOT_REGULAR_FILE')
        rel=path.relative_to(root).as_posix()
        require(rel not in found, 'DUPLICATE_ASSET_PATH')
        found[rel]=hash_file(path)
    require(bool(found), 'ASSET_TREE_EMPTY')
    return found

def assert_union(old, new, union):
    merged=dict(old)
    for rel, digest in new.items():
        require(rel not in merged or merged[rel] == digest, 'OLD_NEW_ASSET_COLLISION')
        merged[rel]=digest
    require(union == merged, 'ASSET_UNION_NOT_COMPLETE_OR_CHANGED')
    return len(merged)

def validate_candidate(stage, plan, baseline):
    for name in ('CANDIDATE', 'NEW_ASSETS'):
        root=getattr(stage,name)
        require(root.is_dir() and not root.is_symlink(), 'CANDIDATE_RELEASE_NOT_FOUND')
    new_build=stage.CANDIDATE/'.next/BUILD_ID'
    require(new_build.is_file() and not new_build.is_symlink() and
            new_build.read_bytes().decode('ascii').strip() == plan['new_build_id'],
            'CANDIDATE_BUILD_ID_MISMATCH')
    keys=stage.js_keys(stage.CANDIDATE)
    require(len(keys)==1, 'CANDIDATE_KEY_COUNT_MISMATCH')
    only_key=next(iter(keys))
    require(re.fullmatch(rb'pk_test_[A-Za-z0-9]{16,240}', only_key) is not None and
            hash_bytes(only_key) == plan['new_public_key_sha256'] and
            only_key.decode() != baseline['active_public']['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'],
            'CANDIDATE_KEY_FINGERPRINT_MISMATCH')
    # Compare selected *actual staged source bytes* with the immutable Git commit.
    for relative in SOURCE_PATHS:
        staged=stage.CANDIDATE / relative
        require(staged.is_file() and not staged.is_symlink(), 'PINNED_APP_FILE_MISSING')
        committed=stage.command(['git','-C',stage.REPO,'show',
                                 FRONT_SHA + ':act_website-main/' + relative],timeout=15)
        require(hash_file(staged)==hash_bytes(committed), 'PINNED_APP_FILE_CHANGED')
    old=directory_map(stage.OLD_ASSETS)
    new=directory_map(stage.CANDIDATE/'.next/static')
    combined=directory_map(stage.NEW_ASSETS)
    count=assert_union(old,new,combined)
    require(not stage.command(['/usr/bin/ss','-H','-ltn','sport = :3005']).strip(),
            'CANDIDATE_PORT_UNEXPECTEDLY_ACTIVE')
    after=stage.local_state()
    for name in ('nginx_sha256','active_build_id','backend_env_sha256','pid'):
        require(after[name] == baseline[name], 'ACTIVE_RELEASE_DRIFT')
    return count

def main():
    try:
        require(os.geteuid() == 0, 'ROOT_READ_ONLY_REQUIRED')
        stage=import_pinned_helper()
        baseline=stage.local_state()
        plan=private_plan(stage.RECORD/'plan.json')
        validate_plan(stage,plan,baseline)
        count=validate_candidate(stage,plan,baseline)
        print('PASS: INACTIVE_FRONTEND_CANDIDATE_VERIFIED')
        print('PASS: REPLACEMENT_TEST_KEY_IN_COMPILED_ASSETS')
        print('PASS: EIGHT_CRITICAL_APP_FILES_MATCH_PINNED_SOURCE')
        print('PASS: STATIC_ASSET_UNION_VERIFIED',count)
        print('PASS: CURRENT_FRONTEND_AND_BACKEND_PRESERVED')
        print('PASS: CANDIDATE_PORT_NOT_ACTIVE')
        print('NO_CHANGES; ACTIVATION_NOT_APPROVED')
        return 0
    except Stop as ex:
        print('STOPPED: '+str(ex)+'; NO_CHANGES',file=sys.stderr)
        return 1
    except Exception:
        print('STOPPED: CANDIDATE_READ_ONLY_VERIFICATION_UNAVAILABLE; NO_CHANGES',file=sys.stderr)
        return 1

if __name__=='__main__':
    sys.exit(main())
