# Build frontend
FROM node:20 AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install
COPY web/frontend/ ./
RUN npm run build

# Build backend
FROM python:3.11-slim
WORKDIR /app

# Install ffmpeg for yt-dlp
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy core logic
COPY core ./core

# Copy backend
COPY web/backend ./web/backend

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./web/frontend/dist

# Expose port
EXPOSE 8000

ENV PYTHONPATH=/app
ENV DOWNLOAD_DIR=/downloads

CMD ["uvicorn", "web.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
