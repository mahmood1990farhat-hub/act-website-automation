# Disposable ACT safety-test environment — phase 1

Prepared 2026-10-01 from website main `23a7e31bee5ff8cb539f973282ddc98f5f99a07d`.
Keep this work on `codex/isolated-backend-tests-20261001`. Do not merge to main:
every main push triggers production frontend deployment, even backend-only edits.

This is a test harness, not a staging website or a complete backend replica.
It executes 11 onboarding handler/AST and 11 shared exception-safety tests, plus four
real Django smoke tests for memory-only email, disposable synthetic SQLite data,
the Python network tripwire and absence of production module imports.
ACT serializers, models, migrations, HTTP routes, PostGIS, Celery and external
services are NOT integrated yet. Passing does not establish signup functionality
or authorize a production deployment. Payment SDKs and credentials are absent.

## Safety boundaries

- Docker runtime network mode is `none`; no host ports, mounts or credentials.
- A Dockerfile-specific deny-by-default build-context allowlist excludes `.env`,
  Firebase files, production settings, database dumps and unrelated source.
- Non-root, read-only container; bounded temporary memory storage; no persistent DB.
- No production settings import. Email is captured in Django memory, not sent.
- Python network guard is defence in depth, not a native-code security boundary.
- Building downloads the Python base image and Django dependencies. Image tags
  and Django range are not a reproducible dependency lock; review/pin before CI use.
- No GitHub workflow, worker, public server, scheduler or paid infrastructure created.

## GitHub-hosted runner preparation

`.github/workflows/isolated-safety-tests.yml` is a manual-only candidate using
`ubuntu-24.04`, contents-read permission, a 10-minute job limit, no production
environment/secrets, exact dispatched SHA checkout and no persisted credentials.
It runs the local regressions/config checks, builds the isolated image and runs
the container. Dependency/image downloads happen before the network-disabled
test runtime. It does not test the complete ACT application.

BLOCKED: this new workflow exists only on the test branch. GitHub's standard
manual trigger requires the workflow on the default branch. Do not merge to
main to enable it, because main pushes trigger frontend production deployment.
No run has been dispatched. A branch-only push trigger would avoid main but is
a change from the approved manual-only design and requires owner approval.
The available connector also has no workflow-dispatch operation.

Five host-side static workflow safety tests can be run from act_backend-main:

```sh
python -m unittest discover -s isolation -p test_workflow.py -v
```

Reference: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

## Run on a disposable Docker-capable development machine

From the repository root (not a production server):

```sh
docker compose -f act_backend-main/isolation/compose.yaml build
docker compose -f act_backend-main/isolation/compose.yaml run --rm tests
```

Do not add production credentials, mounts, networking, Compose overrides or real
customer fixtures. `--rm` removes the completed test container; the local image
and build cache remain. No database volume is created.

Host-only checks, from `act_backend-main`:

```sh
python -m unittest discover -s tests -p test_onboarding_logging.py -v
python -m unittest discover -s tests -p test_shared_exception_safety.py -v
python -m unittest discover -s isolation -p test_config.py -v
```

The second command requires PyYAML. Do not use `manage.py` for this harness.

## Verification status

The 22 source/handler regression tests and six configuration/guard checks passed in the
authoring workspace. Python syntax and YAML parsing passed. Docker and Django
are unavailable there, so image build, container startup and the four Django
smoke tests remain UNEXECUTED. No production deployment or live-data test was
performed for this change.

Next gate: run this container on an authorized disposable runner, then extend
to actual ACT signup with isolated PostGIS and explicit fake integrations before
considering deployment. The existing logging fix covers the step-1 handler's
save exception path. The branch also prepares a fixed-message shared unexpected
exception formatter; see `../tests/SHARED_EXCEPTION_SAFETY.md` for scope limits.
Other callers, logging paths and real application integration still need review.
