#!/bin/bash -e

mkdir -p src/bci_build/package/{postgres,nginx,grafana,mariadb}

curl -o src/bci_build/package/postgres/entrypoint.sh https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh
curl -o src/bci_build/package/postgres/LICENSE https://raw.githubusercontent.com/docker-library/postgres/master/LICENSE

curl -o src/bci_build/package/nginx/docker-entrypoint.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/docker-entrypoint.sh
curl -o src/bci_build/package/nginx/LICENSE https://raw.githubusercontent.com/nginxinc/docker-nginx/master/LICENSE
curl -o src/bci_build/package/nginx/10-listen-on-ipv6-by-default.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/10-listen-on-ipv6-by-default.sh
curl -o src/bci_build/package/nginx/20-envsubst-on-templates.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/20-envsubst-on-templates.sh
curl -o src/bci_build/package/nginx/30-tune-worker-processes.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/30-tune-worker-processes.sh

curl -o src/bci_build/package/grafana/run.sh https://raw.githubusercontent.com/grafana/grafana/main/packaging/docker/run.sh

curl -o src/bci_build/package/mariadb/entrypoint.sh https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/docker-entrypoint.sh
curl -o src/bci_build/package/mariadb/healthcheck.sh https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/healthcheck.sh
