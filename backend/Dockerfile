FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY backend/pyproject.toml backend/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart websockets

# Copy backend code
COPY backend/ backend/

# Copy boards folder
COPY boards/ boards/

# Copy frontend (public folder)
COPY public/ public/

EXPOSE 8000

WORKDIR /app/backend

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
