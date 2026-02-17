#!/bin/sh
# vim:sw=4:ts=4:et

set -e

entrypoint_log() {
    if [ -z "${NGINX_ENTRYPOINT_QUIET_LOGS:-}" ]; then
        echo "$@"
    fi
}

if [ "$1" = "nginx" ] || [ "$1" = "nginx-debug" ]; then
    if /usr/bin/find "/docker-entrypoint.d/" -mindepth 1 -maxdepth 1 -type f -print -quit 2>/dev/null | read v; then
        entrypoint_log "$0: /docker-entrypoint.d/ is not empty, will attempt to perform configuration"

        entrypoint_log "$0: Looking for shell scripts in /docker-entrypoint.d/"
        find "/docker-entrypoint.d/" -follow -type f -print | sort -V | while read -r f; do
            case "$f" in
                *.envsh)
                    if [ -x "$f" ]; then
                        entrypoint_log "$0: Sourcing $f";
                        . "$f"
                    else
                        # warn on shell scripts without exec bit
                        entrypoint_log "$0: Ignoring $f, not executable";
                    fi
                    ;;
                *.sh)
                    if [ -x "$f" ]; then
                        entrypoint_log "$0: Launching $f";
                        "$f"
                    else
                        # warn on shell scripts without exec bit
                        entrypoint_log "$0: Ignoring $f, not executable";
                    fi
                    ;;
                *) entrypoint_log "$0: Ignoring $f";;
            esac
        done

        entrypoint_log "$0: Configuration complete; ready for start up"
    else
        entrypoint_log "$0: No files found in /docker-entrypoint.d/, skipping configuration"
    fi
fi

CURRENT_UID=$(id -u)
if [ "$CURRENT_UID" -gt "0" ]; then
    # Running as Unprivileged User
    entrypoint_log "$0: Running as unprivileged user (UID: $CURRENT_UID). Configuring for unprivileged mode (Port 8080)."

    # Define targets
    CONF_FILES="/etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf"

    for FILE in $CONF_FILES; do
        if [ -w "$FILE" ]; then
            # Check if it actually contains port 80
            if grep -q "listen .*80;" "$FILE"; then
                entrypoint_log "Changing port 80 to 8080 in $FILE"
                # Use a safe writable subdirectory for the swap file
                sed 's/listen\s*80;/listen 8080;/g' "$FILE" > /tmp/client_temp/nginx_swap.conf && \
                cat /tmp/client_temp/nginx_swap.conf > "$FILE" && \
                rm -f /tmp/client_temp/nginx_swap.conf
            fi

            # Redirect temp paths to /tmp if we are editing the main nginx.conf
            if [ "$FILE" = "/etc/nginx/nginx.conf" ]; then
                entrypoint_log "Redirecting NGINX temp paths and setting PID to /tmp in $FILE"
                # Use a safe writable subdirectory for the swap file
                sed -e '/^user/d' \
                    -e 's,^#\?\s*pid\s\+.*;$,pid /var/run/nginx/nginx.pid;,' \
                    -e '/http {/a \    client_body_temp_path /tmp/client_temp;\n    proxy_temp_path /tmp/proxy_temp;\n    fastcgi_temp_path /tmp/fastcgi_temp;\n    uwsgi_temp_path /tmp/uwsgi_temp;\n    scgi_temp_path /tmp/scgi_temp;' \
                    "$FILE" > /tmp/client_temp/nginx_ultra.conf && \
                cat /tmp/client_temp/nginx_ultra.conf > "$FILE" && \
                rm -f /tmp/client_temp/nginx_ultra.conf
                entrypoint_log "$0: Removed 'user' directive and updated PID path."
            fi
        fi
    done

    entrypoint_log "$0: Listening on port 8080."
fi
exec "$@"
