#!/bin/bash -e

mkdir -p src/bci_build/{postgres,nginx,grafana}

curl -o src/bci_build/postgres/entrypoint.sh https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh
curl -o src/bci_build/postgres/LICENSE https://raw.githubusercontent.com/docker-library/postgres/master/LICENSE

curl -o src/bci_build/nginx/docker-entrypoint.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/docker-entrypoint.sh
curl -o src/bci_build/nginx/LICENSE https://raw.githubusercontent.com/nginxinc/docker-nginx/master/LICENSE
curl -o src/bci_build/nginx/10-listen-on-ipv6-by-default.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/10-listen-on-ipv6-by-default.sh
curl -o src/bci_build/nginx/20-envsubst-on-templates.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/20-envsubst-on-templates.sh
curl -o src/bci_build/nginx/30-tune-worker-processes.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/30-tune-worker-processes.sh

curl -o src/bci_build/grafana/run.sh https://raw.githubusercontent.com/grafana/grafana/main/packaging/docker/run.sh
