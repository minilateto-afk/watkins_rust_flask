# Local-only Flask dashboard. Build locally; do not publish this image because
# the source workbook's redistribution permission has not been verified.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . ./

# Distinguish this release from old projects at build time.
RUN echo "Watkins verified release 2026-11-21 - testing real Flask routes" \
    && python verify_release.py

# Rebuild all derived tables from the original workbook during image creation;
# fail the build if data conversion or the bundled regression tests fail.
RUN python prepare_data.py && python -m unittest discover -s tests -v

RUN useradd --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3).read()" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]
