#!/bin/sh

set -e

echo -e "* oO0OoO0OoO0Oo NGINX is starting oO0OoO0OoO0Oo"

CURRENT_UID=$(id -u)
NGINX_CONFIG=/etc/nginx/nginx.conf

if ! grep -q " $NGINX_CONFIG " /proc/self/mountinfo; then
    if [ "$CURRENT_UID" -gt "0" ]; then
        # if the config is not mounted, it will fail and we need to use the non-root one
        NGINX_CONFIG="/etc/nginx/nginx.conf.non-root"
    fi
fi

VERSION=$(/sbin/nginx -v 2>&1 | awk -F'/' '{print $2}')
PORT=$(grep -E -o "listen +[0-9]+" "$NGINX_CONFIG" 2>/dev/null | awk '{print $2}' | head -n1)
PORT=${PORT:-80}
PID=$$
USER=$(whoami)

echo -e "* Configuration loaded from $NGINX_CONFIG"

cat << EOF
    
               .:=++=:..
            .-=********=-.
        ..-+**************+-..
     .:=+********************+=:.
    =******=-=**********+-=******=    
    ******:.  .-*******+. .-******    Nginx Web Server
    ******:    ..=*****=  .:******    
    ******:  .: ..-+***=  .:******    Running in interactive mode
    ******:  .*+.  .=**=  .:******    Port: $PORT
    ******:  .***-   :+=   :******    PID:  $PID
    ******:  .****+:.  :  .:******    User: $USER
    ******:  .******-..   .:******    
    ******:. .*******+:.  .-******    https://nginx.org
    +******==**********+=-+******+    
     .:=**********************=:.
        ..=+**************+=:.
            .-+********+-.
               .:=+*=:..
    
EOF

echo -e "* Server initialized"
echo -e "* Ready to accept connections"

exec /usr/sbin/nginx -c "${NGINX_CONFIG}" -g "daemon off;" "$@"
