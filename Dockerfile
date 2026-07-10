# Multi-stage production build
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS production
LABEL maintainer="Khula Collective Team" version="2.0.0"
WORKDIR /app
RUN groupadd --gid 1000 khula && useradd --uid 1000 --gid khula --shell /bin/bash --create-home khula
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 fonts-liberation fontconfig && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY --chown=khula:khula app.py .
COPY --chown=khula:khula .streamlit/ ./.streamlit/
RUN mkdir -p /app/data && chown -R khula:khula /app
USER khula
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
