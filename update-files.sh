#!/bin/bash -e
# SPDX-License-Identifier: MIT
# Copyright 2022-2024 SUSE LLC
#
# Note: when fetching external files, make sure to include their license declarations!

mkdir -p src/bci_build/package/{postgres,nginx,grafana,mariadb,postfix/entrypoint/ldap,podman}

### postgres: PostgreSQL license
curl -sf -o src/bci_build/package/postgres/LICENSE https://raw.githubusercontent.com/docker-library/postgres/master/LICENSE
curl -sf -o src/bci_build/package/postgres/entrypoint.sh https://raw.githubusercontent.com/docker-library/postgres/master/docker-entrypoint.sh

### nginx BSD-2-Clause
curl -sf -o src/bci_build/package/nginx/LICENSE https://raw.githubusercontent.com/nginxinc/docker-nginx/master/LICENSE
curl -sf -o src/bci_build/package/nginx/docker-entrypoint.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/docker-entrypoint.sh
curl -sf -o src/bci_build/package/nginx/20-envsubst-on-templates.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/20-envsubst-on-templates.sh
curl -sf -o src/bci_build/package/nginx/30-tune-worker-processes.sh https://raw.githubusercontent.com/nginxinc/docker-nginx/master/entrypoint/30-tune-worker-processes.sh

### grafana: AGPL
curl -sf -o src/bci_build/package/grafana/LICENSE https://raw.githubusercontent.com/grafana/grafana/main/LICENSE
curl -sf -o src/bci_build/package/grafana/run.sh https://raw.githubusercontent.com/grafana/grafana/main/packaging/docker/run.sh

### mariadb: GPLv2
command -v jq > /dev/null || { echo "we need jq installed for update to work"; exit 1; }
rm -f src/bci_build/package/mariadb/*/entrypoint.sh src/bci_build/package/mariadb/*/healthcheck.sh
for v in $(jq -r '.mariadb | del(.version_format) | .[]' src/bci_build/package/package_versions.json | cut -d. -f1-2 | sort -u); do
    mkdir -p "src/bci_build/package/mariadb/$v"
    upstream_version=$v
    curl -sf -o "src/bci_build/package/mariadb/$v/LICENSE" "https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/LICENSE"
    curl -sf -o "src/bci_build/package/mariadb/$v/entrypoint.sh" "https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/$upstream_version/docker-entrypoint.sh"
    curl -sf -o "src/bci_build/package/mariadb/$v/healthcheck.sh" "https://raw.githubusercontent.com/MariaDB/mariadb-docker/master/$upstream_version/healthcheck.sh"
done

# TODO add license to upstream helm chart repo and fetch it here
curl -sf -o src/bci_build/package/templates/rmt_helm_chart_readme.j2 https://raw.githubusercontent.com/SUSE/helm-charts/main/rmt-helm/README.md

### postfix: MIT
curl -sf -o src/bci_build/package/postfix/entrypoint/entrypoint.sh https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/entrypoint.sh
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/smtpd_sender_login_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/smtpd_sender_login_maps
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/virtual_alias_domains https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_alias_domains
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/virtual_alias_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_alias_maps
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/virtual_gid_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_gid_maps
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/virtual_mailbox_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_mailbox_maps
curl -sf -o src/bci_build/package/postfix/entrypoint/ldap/virtual_uid_maps https://raw.githubusercontent.com/thkukuk/containers-mailserver/master/postfix/ldap/virtual_uid_maps

patch src/bci_build/package/postfix/entrypoint/entrypoint.sh src/bci_build/package/postfix/entrypoint/sles-entrypoint.patch -o src/bci_build/package/postfix/entrypoint/entrypoint.sles.sh

### podman: Apache-2
curl -sf -o src/bci_build/package/podman/containers.conf https://raw.githubusercontent.com/containers/image_build/main/podman/containers.conf
curl -sf -o src/bci_build/package/podman/podman-containers.conf https://raw.githubusercontent.com/containers/image_build/main/podman/podman-containers.conf
curl -sf -o src/bci_build/package/podman/LICENSE https://raw.githubusercontent.com/containers/image_build/main/LICENSE
