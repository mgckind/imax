FROM python:3-alpine as base
RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev
ENV LIBRARY_PATH=/lib:/usr/lib
FROM base as builder
RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install --install-option="--prefix=/install" -r /requirements.txt

FROM base
RUN adduser explorer -u 1001 -g 1001 -h /home/explorer -s /bin/sh -D
COPY --from=builder /install /usr/local
COPY python_server /home/explorer/server
RUN chown -R 1001:1001 /home/explorer 
WORKDIR /home/explorer/server
USER explorer