# MariaDB Client container image

[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

MariaDB is an open-source, multi-threaded, relational database management system. It's a backward-compatible branch of the MySQL Community Server that provides a drop-in replacement for MySQL.

This image contains the [MariaDB client](https://mariadb.com/kb/en/mariadb-command-line-client/) and utilities.

## Usage

To connect to a MariaDB instance, run the following command:

```ShellSession
$ podman run -it --rm registry.suse.com/suse/rmt-mariadb-client:10.11 mariadb -h $HOST_IP -u root -p
```

Use the command below to dump all databases:

```ShellSession
$ podman run -it --rm registry.suse.com/suse/rmt-mariadb-client:10.11 mariadb-dump $HOST_IP -p --all-databases > my-dump.sql
```

## Utilities

The following utilities are available in the image:

- mariadb
- mariadb-admin
- mariadb-check
- mariadb-dump
- mariadb-import
- mariadb-show
- mariadbd-safe-helper

## Backup and restore

The MariaDB Knowledge Base [Container Backup and Restoration](https://mariadb.com/kb/en/container-backup-and-restoration/) provides further information on how to perform backup and restore.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.