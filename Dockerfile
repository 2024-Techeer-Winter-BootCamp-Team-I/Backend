FROM python:3.10

ENV PYTHONUNBUFFERED 1

WORKDIR /DevSketch-Backend

COPY ./requirements.txt /requirements.txt

RUN pip install --upgrade -r /requirements.txt

COPY . ./

RUN python manage.py collectstatic --noinput
