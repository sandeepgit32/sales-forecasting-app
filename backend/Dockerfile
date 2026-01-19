FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps (for some packages)
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev gcc curl git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && pip install -r /app/requirements.txt

# copy backend code
COPY . /app

WORKDIR /app
EXPOSE 5000

# Make worker scripts executable (if they exist)
RUN chmod +x /app/etl_service/etl_worker.sh /app/forecast_service/forecast_worker.sh || true

# Default command will run the Flask API; workers override via docker-compose command
CMD ["gunicorn", "upload_service.app:app", "-b", "0.0.0.0:5000"]
