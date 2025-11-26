FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


RUN apt update 
RUN apt upgrade -y 
RUN apt install -y nano unixodbc unixodbc-dev

WORKDIR /app

COPY requirements.txt .


RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . .


