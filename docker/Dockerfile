#!/bin/bash
FROM python:3.8.7

# Install nano and curl 
RUN apt-get update -y
# RUN apt-get install nano curl gnupg wget cron tar -y

# Install pips
RUN pip3 install mysql-connector-python==8.0.22 python-dotenv paho-mqtt==1.6.1 cryptography==3.4.8 

# Add a non-root user and switch to it
# https://stackoverflow.com/a/70520801
RUN addgroup --gid 1001 nonrootgroup && adduser --system --no-create-home --uid 1001 --gid 1001 nonroot
USER nonroot
