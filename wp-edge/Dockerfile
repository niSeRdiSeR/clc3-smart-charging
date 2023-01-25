FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
COPY requirements.txt /app
COPY wp-edge.py /app

WORKDIR /app
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "wp-edge.py"]
