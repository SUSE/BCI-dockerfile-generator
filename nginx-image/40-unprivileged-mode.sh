#!/bin/sh

CURRENT_UID=$(id -u)

if ! grep -q " /etc/nginx/nginx.conf " /proc/self/mountinfo; then
    if [ "$CURRENT_UID" -gt "0" ]; then
        echo "$0: Running as unprivileged user ($CURRENT_UID)!"
        echo "$0: /etc/nginx/nginx.conf it not mounted!"
        echo "$0: Start nginx with the appropriate configuraion found at /etc/nginx/nginx.conf.non-root"
    fi
fi
