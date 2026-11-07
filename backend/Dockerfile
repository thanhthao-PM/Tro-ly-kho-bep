# ==============================================================================
# DOCKERFILE CHO BACKEND (PYTHON 3.11 + FASTAPI + SQLALCHEMY 2.X)
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Cài đặt curl để phục vụ container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn Backend
COPY . .

# Expose cổng 8000
EXPOSE 8000

# Health check dịch vụ FastAPI
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Khởi chạy Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
