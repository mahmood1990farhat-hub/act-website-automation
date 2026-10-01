# Shared unexpected-exception safety patch — prepared, not deployed

2026-10-01. Follow-up on the isolated test branch only.

The inspected `format_exception_error` logged exception text and traceback and
returned raw/truncated values for several error types. `EMADBaseView` routes
unexpected exceptions through this shared helper, including failures outside
the step-1 onboarding save block.

Replace only this formatter with a fixed English/Arabic response and constant
log event. Do not evaluate exception text, repr, class names or tracebacks.
The response envelope, HTTP 500, safe caller-supplied custom message and explicit
validation-error functions remain unchanged. Unexpected exceptions that formerly
produced specific payment, database or phone messages now return a generic error;
expected user-correctable cases should use explicit validation responses.

Eleven new stdlib tests run actual helper AST with response/import stubs. They
cover secret-bearing provider/database/network errors, bilingual output, chained
exceptions, ErrorDetail-lookalike strings, hostile __str__/__repr__, response
shape and existing validation formatting. They are not Django/HTTP tests.

Scope limits: caller-supplied custom_message must be safe static text. Other
logging statements, middleware, validation payloads, ParseError/NotFound paths,
third-party monitoring and historical production logs are not audited or fixed
by this change. No historical exposure was established and no real logs read.
The constant log sacrifices error detail; a separately reviewed correlation-ID
and safe event classification design may restore diagnostics without raw data.

Run from act_backend-main:

```sh
python -m unittest discover -s tests -p 'test_*logging.py' -v
python -m unittest discover -s tests -p test_shared_exception_safety.py -v
python -m unittest discover -s isolation -p test_config.py -v
```

The container allowlist and runner include these tests. Docker image build and
four real Django smoke tests remain unexecuted in this workspace. Full backend
integration testing is still a release gate. Do not merge to main or deploy on
the strength of these stubbed tests: main pushes trigger frontend production.
