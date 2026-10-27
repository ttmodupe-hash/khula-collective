# Khula Collective v4.0 — Railway Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    tesseract-ocr \
    gosu \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY khula_config.py .
COPY khula_utils.py .
COPY khula_pages1.py .
COPY khula_pages2.py .
COPY khula_pages3.py .
COPY khula_ai_engine.py .
COPY khula_id_engine.py .
COPY khula_security.py .
COPY khula_advisory_core.py .
COPY khula_market_data.py .
COPY khula_member_services.py .
COPY khula_reporting.py .
COPY khula_governance.py .
COPY khula_sarb.py .
COPY khula_public_markets.py .
COPY khula_invitations.py .
COPY khula_bank_import.py .
COPY khula_account.py .
COPY khula_recovery.py .
COPY khula_compliance.py .
COPY khula_bank_access.py .
COPY khula_applications.py .
COPY khula_compass.py .
COPY khula_membership_receipts.py .
COPY khula_launch_center.py .
COPY khula_owner_access.py .
COPY khula_intelligence.py .
COPY khula_entrypoint.sh /usr/local/bin/khula-entrypoint
COPY .streamlit/ .streamlit/

# Installable, online-only Progressive Web App shell. Static content is public
# branding/help only: never cache or ship the club's private SQLite ledger.
COPY static/ static/
COPY scripts/generate_pwa_icons.py scripts/
COPY scripts/patch_streamlit_pwa.py scripts/
COPY scripts/harden_install_page.py scripts/
RUN python scripts/harden_install_page.py --apply \
    && python scripts/generate_pwa_icons.py --output-dir /app/static \
    && python scripts/patch_streamlit_pwa.py --apply

# Drop privileges for the application after mounting the writable ledger volume.
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chmod 755 /usr/local/bin/khula-entrypoint
USER root

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# Railway sets PORT env var automatically
EXPOSE ${PORT:-8501}

CMD ["/usr/local/bin/khula-entrypoint"]
