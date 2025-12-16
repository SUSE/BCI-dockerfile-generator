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

# Ensure PID path is set to /var/run/nginx.pid for both privileged and unprivileged users
sed -i 's,^#\?\s*pid\s\+.*;$,pid /var/run/nginx/nginx.pid;,' /etc/nginx/nginx.conf
# modify temp paths for both privileged and unprivileged users
sed -i "/^http {/a \        proxy_temp_path /tmp/proxy_temp;\n        client_body_temp_path /tmp/client_temp;\n        fastcgi_temp_path /tmp/fastcgi_temp;\n        uwsgi_temp_path /tmp/uwsgi_temp;\n        scgi_temp_path /tmp/scgi_temp;\n" /etc/nginx/nginx.conf

CURRENT_UID=$(id -u)
if [ "$CURRENT_UID" -gt "0" ]; then
    # Running as Unprivileged User
    entrypoint_log "$0: Running as unprivileged user (UID: $CURRENT_UID). Configuring for unprivileged mode (Port 8080)."

    # Remove 'user' directive (unprivileged users can't switch users)
    sed -i '/^user/d' /etc/nginx/nginx.conf
    entrypoint_log "$0: Removed 'user' directive for unprivileged worker."

    sed -i 's/listen \(.*\)80;/listen \18080;/' /etc/nginx/conf.d/default.conf 2>/dev/null || \
    sed -i 's/listen \(.*\)80;/listen \18080;/' /etc/nginx/nginx.conf 2>/dev/null || true
    entrypoint_log "$0: Listening on port 8080."
fi

exec "$@"
