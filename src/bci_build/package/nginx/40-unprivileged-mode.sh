#!/bin/sh

set -e

ME=$(basename "$0")
CURRENT_UID=$(id -u)

if [ "$CURRENT_UID" -gt "0" ]; then
    echo "$ME: Running as unprivileged user (UID: $CURRENT_UID)."

    CONF_FILES="/etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf"

    for FILE in $CONF_FILES; do
        [ -f "$FILE" ] || continue

        if [ -w "$FILE" ]; then
            if grep -E -q 'listen\s+80;' "$FILE"; then
                sed -i 's/listen\s*80;/listen 8080;/g' "$FILE"
                echo "$ME: NGINX port was updated from 80 to 8080!"
            elif grep -q 'listen 8080;' "$FILE"; then
                echo "$ME: NGINX port is already set to 8080. No changes needed."
            else
                echo "$ME: NGINX port was not updated. Failed to find listen parameter!"
            fi

            if [ "$FILE" = "/etc/nginx/nginx.conf" ]; then
                if grep -E -q '^user\b' "$FILE"; then
                    sed -i -e '/^user/d' "$FILE"
                    echo "$ME: Removed 'user' directive."
                else
                    echo "$ME: Skipping user modification. The 'user' directive was not found!"
                fi

                if grep -E -q '^#?\s*pid\s+' "$FILE"; then
                    sed -i -e 's,^#\?\s*pid\s\+.*;$,pid /tmp/nginx/nginx.pid;,' "$FILE"
                    echo "$ME: Updated PID path to '/tmp/nginx/nginx.pid'."
                else
                    echo "$ME: Skipping PID modification. pid directive not found!"
                fi

                required="client_body_temp_path proxy_temp_path fastcgi_temp_path uwsgi_temp_path scgi_temp_path"

                for directive in $required; do
                    if grep -Eq "^[[:space:]]*${directive}[[:space:]]+" "$FILE"; then
                        echo "$ME: Skipping ${directive} modification. Already set."
                    else
                        sed -i "/http {/a\    ${directive} /tmp/${directive%_path};" "$FILE"
                        echo "$ME: Redirected ${directive} to '/tmp/${directive%_path}'."
                    fi
                done
            fi
        else
            echo "$ME: Permission denied for user $CURRENT_UID: $FILE"
            exit 1
        fi
    done
fi
