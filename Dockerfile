FROM debian:bookworm-slim

RUN \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        calibre \
        python3-requests \
        curl \
        python3-aiohttp \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
COPY FeedlyToCalibre.recipe /FeedlyToCalibre.recipe
COPY server.py /server.py

CMD [ "/entrypoint.sh" ]
