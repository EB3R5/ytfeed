# Server target. Build from the repo root:
#   docker build -f packaging/docker/Dockerfile -t ytfeed .
# The image carries its own config.toml (packaging/docker/config.toml) with container paths; the
# compose.yml mounts ./data (SQLite), ./secrets (OAuth token), the vault at /rag/raw and the
# NotebookLM profile at NOTEBOOKLM_HOME. Both Google logins happen on the host, never in here.
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ytfeed ./ytfeed
# editable: the package runs from /app, so ytfeed.config.PROJECT_ROOT resolves to /app (config.toml, data/, secrets/)
RUN pip install --no-cache-dir -e .
COPY packaging/docker/config.toml ./config.toml
# HOME on the mounted data dir: the container may run as the host uid (no passwd entry), and
# yt-dlp / google-auth want a writable cache. NOTEBOOKLM_HOME replaces ~/.notebooklm.
ENV HOME=/app/data \
    XDG_CACHE_HOME=/app/data/.cache \
    NOTEBOOKLM_HOME=/nlm
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"
CMD ["python", "-m", "ytfeed", "serve", "--host", "0.0.0.0", "--port", "8000"]
