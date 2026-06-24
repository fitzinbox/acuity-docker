FROM --platform=linux/amd64 postgres:16

WORKDIR /usr/root

RUN apt-get update \
    && apt-get install -y postgresql-16-orafce \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5432