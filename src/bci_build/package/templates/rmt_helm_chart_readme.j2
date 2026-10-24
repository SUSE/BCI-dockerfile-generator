# Purpose

This chart deploys a SUSE Repository Mirroring Tool (RMT) server on Kubernetes.
It is tested on K3s but should work on any Kubernetes distribution.

## Overview

To deploy SUSE RMT on top of Kubernetes, each component of the stack is deployed in a dedicated container using a
Helm chart.

### Repository Mirroring Tool (SUSE RMT) server

A containerized version of the SUSE RMT application that can pass its configuration via Helm values. Because persistent storage resides on a persistent volume, you need to adjust the volume size according to the number of repositories you need to mirror.

### MariaDB

The database back-end for SUSE RMT.
If needed, RMT creates the database and tables at startup, so no specific
post-installation task is required for it to be usable. Passwords are
self-generated, unless explicitly specified in the values file, or
provided via externally-managed Secrets (see
[Externally-managed Secrets](#externally-managed-secrets)).

### NGINX

The web server with appropriate configuration for RMT routes. Having a correctly
configured web server right from the start allows you to target your ingress traffic
(for RMT) to directly to the server. You don't have to configure ingress for RMT specific
paths handling, as NGINX is configured to do that.

## Prerequisites

- a running Kubernetes cluster
- helm command configured to interact with the cluster

The Helm chart can be obtained using the following command:

`helm pull oci://registry.suse.com/suse/rmt-helm`

## Custom mandatory values

Certain values of the chart do not have any defaults:
- SCC mirroring credentials (refer to [more information](https://documentation.suse.com/sles/html/SLES-all/cha-rmt-mirroring.html#sec-rmt-mirroring-credentials) for more information) — required only when `secrets.create` is `true` (the default). When Secrets are managed externally, see [Externally-managed Secrets](#externally-managed-secrets).
- list of products to mirror
- list of products not to mirror
- list of repos to mirror
- list of repos not to mirror
- DNS name used to reach the RMT server
- configured [storage](https://kubernetes.io/docs/concepts/storage/)

Before deploying the chart, you must fill a custom values file.

The following example enables ingress with TLS. The `create-certs.sh` script
supplied with the Helm chart can be used
to create self-signed certificates and add them to Kubernetes as a usable TLS
secret.

```
cat << EOF > myvalues.yaml
---
app:
  storage:
    class: my-storage-class
  scc:
    username: UXXXXXXX
    password: PASSXXXX
    products_enable:
      - SLES/15.3/x86_64
      - sle-module-python2/15.3/x86_64
    products_disable:
      - sle-module-legacy/15.3/x86_64
      - sle-module-cap-tools/15.3/x86_64
    repos_enable:
      - 1743 # SLE-Live-Patching12-Pool for sle-12-x86_64
      - 7434
      - 7437
    repos_disable:
      - 7940
front:
  enabled: true
ingress:
  enabled: true
  hosts:
    - host: chart-example.local
      paths:
        - path: "/"
          pathType: Prefix
  tls:
  - secretName: rmt-cert
    hosts:
    - chart-example.local
db:
  storage:
    class: my-storage-class
EOF
```

The required values in the custom value file are as follows:

- `app.scc.password` SUSE Customer Center proxy password. Required only when `secrets.create` is `true` (the default). The password string must be in quotes. If the quote character `"` is part of the string, it has to be escaped with `\`.
- `app.scc.username` SUSE Customer Center proxy user name. Required only when `secrets.create` is `true` (the default). The user name string must be quotes. If the quote character `"` is part of the string, it has to be escaped with `\`.
- `app.scc.products_enable` List of products to enable for mirroring.
- `app.scc.products_disable` list of products to exclude from mirroring.
- `app.scc.repos_enable` List of repos to enable for mirroring.
- `app.scc.repos_disable` List of repos to exclude from mirroring.
- `app.storage.class` Kubernetes storageclass.
- `db.storage.class` Kubernetes storageclass.
- `front.enabled` Enable or disable front.
- `ingress.enabled` Enable or disable ingress. Also enable "front" if you want "ingress".
- `ingress.hosts[0]` DNS name at which the RMT service is be accessible from clients.
- `ingress.tls[0].hosts[0]` DNS name at which the RMT service is be accessible from clients.
- `ingress.tls[0].secretName` TLS ingress certificate.

## Secret names and external Secret management

By default (`secrets.create: true`) this chart renders two Kubernetes Secrets.
Their names come from `{{ include "rmt.fullname" . }}` (defined in
`templates/_helpers.tpl`), suffixed with `-db` and `-app`:

- `<fullname>-db` — keys: `password`, `rootPassword` (MariaDB credentials)
- `<fullname>-app` — keys: `username`, `password` (SCC credentials)

For the common case `helm install rmt ./rmt-helm`, the names resolve to
`rmt-db` and `rmt-app` — the same names referenced by the Deployment and
CronJob templates. When the chart creates the Secrets itself
(`secrets.create: true`), these default names are always used.

### Externally-managed Secrets

To let another component (for example, HashiCorp Vault Secrets Operator managed
by a separate Helm chart) own those Secrets, set `secrets.create: false`. In
that mode you may point the chart at pre-existing Secrets that use self-defining
names via `secrets.existingDbSecret` and `secrets.existingAppSecret`:

```yaml
secrets:
  create: false
  existingDbSecret: rmt-vault-db
  existingAppSecret: rmt-vault-scc
```

When `secrets.create` is `false`:

- This chart no longer renders `10-db-secrets.yaml` / `20-app-secrets.yaml`.
- `app.scc.username` and `app.scc.password` are no longer required in your
  values file — they must be present in the externally-created Secret instead.
- You must ensure the required Secrets already exist in the target namespace
  **before** installing this chart, with these keys:

  | Secret name | Keys |
  |---|---|
  | `existingDbSecret` (default `<fullname>-db`) | `password`, `rootPassword` |
  | `existingAppSecret` (default `<fullname>-app`) | `username`, `password` |


## Deploying

`helm install rmt ./helm -f myvalues.yaml`

## Further info

For more information on using RMT, refer to the [RMT Guide](https://documentation.suse.com/sles/html/SLES-all/book-rmt.html).
