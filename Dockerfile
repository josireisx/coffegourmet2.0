FROM python:3.11

RUN apt-get update && apt-get -y install tzdata git

RUN ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime

RUN dpkg-reconfigure -f noninteractive tzdata

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
COPY main.py .
COPY database.db .
RUN mkdir templates
COPY templates/index.html templates/
RUN mkdir static
COPY static/style.css static/


RUN pip install -r requirements.txt

CMD ["fastapi", "run", "main.py"]
