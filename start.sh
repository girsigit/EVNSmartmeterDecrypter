#!/bin/bash
CONTAINER_NAME=smartmeter-decrypter
CONTAINER_PATH=$PWD

IMAGE_NAME=${CONTAINER_NAME}-image

# Stop and remove the old container
docker stop ${CONTAINER_NAME}
docker rm ${CONTAINER_NAME}

# Build the new one
docker build -t ${IMAGE_NAME} ./docker 

# Start it
docker run \
--name ${CONTAINER_NAME} \
-v ${CONTAINER_PATH}/decoder:/home/decoder \
-v ${CONTAINER_PATH}/../server.env:/server.env \
--cpus="0.25" \
-d \
--restart unless-stopped \
${IMAGE_NAME} \
python /home/decoder/ProcessSmartmeter.py
