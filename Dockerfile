FROM python:3.7-alpine

ARG UID=1501
ARG GID=1501

ARG WH_PORT=60000
ENV WH_PORT ${WH_PORT}

# enables proper stdout flushing
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apk add --no-cache \
	git

# avoid cache invalidation after copying entire directory
COPY requirements.txt .

RUN apk add --no-cache --virtual build-deps \
		gcc \
		musl-dev && \
    pip install --no-cache-dir --disable-pip-version-check -r requirements.txt && \
    apk del build-deps

EXPOSE ${WH_PORT}

RUN addgroup -g $GID -S tarakania && \
    adduser -u $UID -S discord-bot -G tarakania

COPY . .

RUN chown -R $GID:$UID /code
USER $UID

ENTRYPOINT ["python", "tarakania_rpg/main.py"]
