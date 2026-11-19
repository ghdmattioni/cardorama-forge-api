FROM python:3.12-slim-bookworm
ARG FORGE_VERSION=2.0.16
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/home/cardorama FORGE_JAR=/opt/forge/forge.jar FORGE_HEAP_MB=512
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless ca-certificates curl bzip2 tar && rm -rf /var/lib/apt/lists/*
COPY docker/install-forge.sh /usr/local/bin/install-forge
RUN chmod +x /usr/local/bin/install-forge && FORGE_VERSION=${FORGE_VERSION} install-forge
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py parsing.py details.py ./
COPY examples/ ./examples/
RUN useradd --create-home --home-dir /home/cardorama --shell /usr/sbin/nologin cardorama && chown -R cardorama:cardorama /app /opt/forge /home/cardorama
USER cardorama
EXPOSE 8080
CMD ["sh","-c","exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
