# Stage 1: build the frontend (back office, estimate page, widget)
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: backend + built frontend + built website, one image for both processes
# python:3.13-slim, pinned by digest; bump the digest when you rebuild with --pull
FROM python:3.13-slim@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/mpl
WORKDIR /app
COPY backend/requirements.lock ./backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist
COPY frontend/public/brand ./frontend/public/brand
COPY frontend/public/favicon.png frontend/public/apple-touch-icon.png ./frontend/public/
COPY site/ ./site/
RUN python site/build.py
# an unprivileged user; the data volume must be owned by it (chown -R 10001:10001 data on the host)
RUN useradd -r -u 10001 -d /tmp -s /usr/sbin/nologin app && mkdir -p /app/data && chown -R app:app /app/data
ENV SOLARAPP_DATA_DIR=/app/data \
    SOLARAPP_STATIC_DIR=/app/frontend/dist \
    SOLARAPP_SITE_DIR=/app/site/dist
VOLUME ["/app/data"]
EXPOSE 8000
USER app
WORKDIR /app/backend
CMD ["uvicorn", "solarapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
