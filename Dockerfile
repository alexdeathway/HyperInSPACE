FROM ubuntu:22.04

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NOWARNINGS="yes"


RUN apt-get update \
  && apt-get install -y --no-install-recommends  build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get -y install python3-pip && apt-get install -y python3-pyqt5 

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/requirements.txt \
    && useradd -U qtuser 


WORKDIR /app
COPY . .

CMD [ "python3", "Main.py" ]
