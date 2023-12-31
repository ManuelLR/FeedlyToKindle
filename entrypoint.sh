#!/bin/bash

set -ex

cd /output

OUTPUT_FILE_NAME="FeedlyToCalibre.mobi"

ebook-convert \
    /FeedlyToCalibre.recipe \
    ${OUTPUT_FILE_NAME} \
    --verbose --output-profile=kindle_pw3

# Push file to http server
curl -F "file=@${OUTPUT_FILE_NAME}" https://tmpfiles.org/api/v1/upload

sleep 999d
