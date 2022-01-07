#!/bin/bash -e

curl -o postgres-entrypoint.sh https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh
curl -o postgres-LICENSE https://raw.githubusercontent.com/docker-library/postgres/master/LICENSE

test -d nginx || mkdir nginx
curl -o nginx/docker-entrypoint.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/docker-entrypoint.sh
curl -o nginx/LICENSE https://raw.githubusercontent.com/nginxinc/docker-nginx/master/LICENSE
curl -o nginx/10-listen-on-ipv6-by-default.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/10-listen-on-ipv6-by-default.sh
curl -o nginx/20-envsubst-on-templates.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/20-envsubst-on-templates.sh
curl -o nginx/30-tune-worker-processes.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/30-tune-worker-processes.sh
