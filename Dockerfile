FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY config/ ./config/
COPY data/imported/ ./data/imported/
COPY data/derived/ ./data/derived/
COPY data/research/benchmarks/ ./data/research/benchmarks/
COPY data/models/terrain_proxy/ ./data/models/terrain_proxy/
COPY data/boundaries/nashik_panchayats_covariates.geojson ./data/boundaries/nashik_panchayats_covariates.geojson
COPY data/panchayat_covariates.csv ./data/panchayat_covariates.csv
COPY --from=frontend /web/dist ./frontend/dist
ENV DISTRICT_CACHE_DIR=/tmp/nashik-district-cache
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
