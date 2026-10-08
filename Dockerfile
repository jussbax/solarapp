# Stage 1: build the frontend
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: backend + built frontend
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist
COPY frontend/public/brand ./frontend/public/brand
COPY frontend/public/favicon.png frontend/public/apple-touch-icon.png ./frontend/public/
COPY site/ ./site/
RUN python site/build.py
ENV SOLARAPP_DATA_DIR=/app/data \
    SOLARAPP_STATIC_DIR=/app/frontend/dist
VOLUME ["/app/data"]
EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "solarapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
