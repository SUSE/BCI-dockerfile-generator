#!/bin/bash

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] $@"
}

trap 'log "Received SIGTERM, exiting PulseAudio"; kill -TERM $PA_PID; wait $PA_PID; exit 0' SIGTERM
trap 'log "Received SIGINT, exiting PulseAudio"; kill -TERM $PA_PID; wait $PA_PID; exit 0' SIGINT

chown root:audio /dev/snd/*

# Start pulseaudio in foreground and capture its PID
/usr/bin/pulseaudio -vvv --log-target=stderr &
PA_PID=$!

wait $PA_PID
log "PulseAudio exited"
