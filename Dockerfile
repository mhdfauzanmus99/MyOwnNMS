# syntax=docker/dockerfile:1

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.9-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NMS_HOST=0.0.0.0 \
    NMS_PORT=8000

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh && mkdir -p /app/data

EXPOSE 8000 1161/udp 1162/udp 1163/udp
VOLUME ["/app/data"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
