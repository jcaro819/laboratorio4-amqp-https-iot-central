FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tcpdump ca-certificates \
        gcc libc6-dev cmake make swig libssl-dev pkg-config \
    && pip install --no-cache-dir requests python-dotenv paho-mqtt python-qpid-proton \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/scripts
