#!/bin/sh
# Volume ownership must be corrected before dropping container privileges.
set -eu
if [ -d "${KHULA_VOLUME_MOUNT:-/data}" ]; then
  chown appuser:appuser "${KHULA_VOLUME_MOUNT:-/data}"
  chmod 700 "${KHULA_VOLUME_MOUNT:-/data}"
fi
export HOME=/home/appuser
exec gosu appuser streamlit run app.py \
  --server.port="${PORT:-8501}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=true \
  --server.enableXsrfProtection=true
