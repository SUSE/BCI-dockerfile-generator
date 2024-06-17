# 389 Directory Server container image

## Description

[389 Directory Server](https://www.port389.org/) is a highly usable, fully featured, reliable and secure LDAP server implementation.

## Usage

By default, the image launches 389 Directory Server with the same configuration that comes with the SUSE Linux Enterprise Server, with one exception, a pre-configured Name Service Switch (NSS) configuration file (`/etc/nsswitch.conf`) in included.

```ShellSession
$ podman run -it --rm -p 3389:3389 -p 3636:3636 registry.opensuse.org/opensuse/389-ds:%%389ds_version%%
```

## Volumes

The database is stored in the directory `/data`. A new empty database will be created on container startup unless an existing database is already present in `/data`.

To mount a host directory as a volume for your database, run the following command:

```ShellSession
$ podman run -it --rm -v /my/own/datadir:/data:Z -p 3389:3389 -p 3636:3636 registry.opensuse.org/opensuse/389-ds:%%389ds_version%%
```

## Certificates

By default, the container will use a self-signed CA certificate and a server certificate signed by that CA.

A custom TLS certificate should be placed in `/data/tls/server.crt` and the key should be placed in and `/data/tls/server.key`.
The CA certificates should be placed under `/data/tls/ca/` in separate files, i.e., `/data/tls/ca/ca1.crt` and `/data/tls/ca/ca2.crt`.

## Environment variables

### DS_ERRORLOG_LEVEL

This optional environment variable can be used to set the log level for `ns-slapd` (default is `266354688`).

### DS_DM_PASSWORD

This optional environment variable can be used to set the `cn=Directory Manager` password (default password is generated randomly).
The default randomly generated password can be viewed in the setup log.

### DS_MEMORY_PERCENTAGE

This optional environment variable can be used to set the LDBM autotune percentage (`nsslapd-cache-autosize`) (default is unset).

### DS_REINDEX

This optional environment variable can be used to run a database re-index task. Set the value to `1` to enable the task (default is disabled).

### DS_SUFFIX_NAME

This optional environment variable can be used to set the default database suffix name for `basedn` (default one is derived from the hostname).

### DS_STARTUP_TIMEOUT

This optional environment variable can be used to change the amount of time to wait for the instance to start (default is `60` seconds).

### DS_STOP_TIMEOUT

This optional environment variable can be used to change the amount of time to wait for the instance to stop (default is `60` seconds).

## Health, liveness, and readiness

There is one explicit health check added to the container image. This check will verify if the service is misconfigured, if `ns-slapd` is running, and if the LDAPI is functional.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [openSUSE Tumbleweed](https://get.opensuse.org/tumbleweed/).
