FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    build-essential \
    netcat-openbsd \  
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY . /app/

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]