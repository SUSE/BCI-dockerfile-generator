#!/bin/bash -e

mkdir -p src/bci_build/package/{postgres,nginx,grafana,mariadb}
mkdir -p src/bci_build/package/{postgres,nginx,grafana,mariadb,postfix/entrypoint/ldap}

curl -o src/bci_build/package/postgres/entrypoint.sh https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh
curl -o src/bci_build/package/postgres/LICENSE https://raw.githubusercontent.com/docker-library/postgres/master/LICENSE

curl -o src/bci_build/package/nginx/docker-entrypoint.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/docker-entrypoint.sh
curl -o src/bci_build/package/nginx/LICENSE https://raw.githubusercontent.com/nginxinc/docker-nginx/master/LICENSE
curl -o src/bci_build/package/nginx/20-envsubst-on-templates.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/20-envsubst-on-templates.sh
curl -o src/bci_build/package/nginx/30-tune-worker-processes.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/30-tune-worker-processes.sh

curl -o src/bci_build/package/grafana/run.sh https://raw.githubusercontent.com/grafana/grafana/main/packaging/docker/run.sh

curl -o src/bci_build/package/mariadb/entrypoint.sh https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/docker-entrypoint.sh
curl -o src/bci_build/package/mariadb/healthcheck.sh https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/healthcheck.sh

curl -o src/bci_build/package/templates/rmt_helm_chart_readme.j2 https://raw.githubusercontent.com/SUSE/helm-charts/main/rmt-helm/README.md

curl -o src/bci_build/package/postfix/entrypoint/entrypoint.sh https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/entrypoint.sh
curl -o src/bci_build/package/postfix/entrypoint/ldap/smtpd_sender_login_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/smtpd_sender_login_maps
curl -o src/bci_build/package/postfix/entrypoint/ldap/virtual_alias_domains https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_alias_domains
curl -o src/bci_build/package/postfix/entrypoint/ldap/virtual_alias_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_alias_maps
curl -o src/bci_build/package/postfix/entrypoint/ldap/virtual_gid_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_gid_maps
curl -o src/bci_build/package/postfix/entrypoint/ldap/virtual_mailbox_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_mailbox_maps
curl -o src/bci_build/package/postfix/entrypoint/ldap/virtual_uid_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_uid_maps
