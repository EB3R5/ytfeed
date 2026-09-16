# Server target. Build from the repo root:
#   docker build -f packaging/docker/Dockerfile -t ytfeed .
# Not wired into homelab compose yet — see packaging/README.md for the host-state mounts
# (config.toml, secrets/, data/, the RAG dir, ~/.notebooklm) it needs at run time.
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md config.example.toml ./
COPY ytfeed ./ytfeed
RUN pip install --no-cache-dir .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "ytfeed.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
