FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# Build-time dependency downloads only. Runtime has no network or service keys.
RUN pip install --no-cache-dir 'Django>=4.2,<5.0'
COPY isolation /app/isolation
COPY tests/test_onboarding_logging.py /app/tests/test_onboarding_logging.py
COPY tests/test_shared_exception_safety.py /app/tests/test_shared_exception_safety.py
COPY utils/common/error_handlers.py /app/utils/common/error_handlers.py
COPY apps/drivers/views/onboarding_views.py /app/apps/drivers/views/onboarding_views.py
USER 65534:65534
CMD ["python", "-m", "isolation.run"]
