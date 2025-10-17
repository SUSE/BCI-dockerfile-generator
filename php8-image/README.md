# The PHP 8 container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

PHP is a general-purpose scripting language used primarily for server-side web
development. It can be used directly, embedded in HTML files, or executed via a
server-side Apache2 module or CGI scripts.

## How to use the image

This image ships with the PHP interpreter as the entrypoint. The image is
intended to be used to execute PHP scripts or PHP commands directly.

To launch an interactive shell in a container, use the following command:
```ShellSession
$ podman run --rm -it registry.suse.com/bci/php:8
Interactive mode enabled

php > echo 5+8;
13
```

You can also use the container instead of the PHP
interpreter to execute PHP scripts:
```ShellSession
$ cat /tmp/test.php
<?php
echo 5+8
$ podman run --rm -it -v /tmp/test.php:/src/test.php:Z \
    registry.suse.com/bci/php:8 -f /src/test.php
13
```

## How to install PHP extensions

PHP extensions must be installed using the `zypper` package manager. PHP
extensions are named using the `php8-$extension_name` scheme,
and they can be installed as follows:

```Dockerfile
FROM registry.suse.com/bci/php:8

RUN zypper -n in php8-gd php8-intl
```

Alternatively, you can use the `docker-php-ext-install` script. It is provided
for compatibility with the [PHP DockerHub Image](https://hub.docker.com/_/php)
but it uses zypper to install the extensions from RPMs. It is provided for
compatibility reasons and can be used similar to the script from PHP DockerHub
image:

```Dockerfile
FROM registry.suse.com/bci/php:8

RUN docker-php-ext-install gd intl
```

## How to install PECL extensions

[PECL](https://pecl.php.net/) is a package repository hosting PHP extensions. It
can be used as an alternative source to obtain PHP extensions, but without any
guarantee of interoperability with this image and without any official support.

Install PECL extensions as follows:

```Dockerfile
FROM registry.suse.com/bci/php:8

RUN set -euo pipefail; \
    zypper -n in $PHPIZE_DEPS php8-pecl; \
    pecl install APCu-5.1.21;
```

**Note:** Building an extension may require installing its dependencies first.


## Compatibility with the DockerHub Image

The following scripts ship with the image to keep it compatible with the
DockerHub image: `docker-php-source`, `docker-php-ext-configure`,
`docker-php-ext-enable`, and `docker-php-ext-install`.
The script `docker-php-ext-install` performs an actual job, all others are
just no-operation scripts for interoperability.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
