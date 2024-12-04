
# The SUSE Linux Enterprise FIPS-140-3 container image

![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description


This base container image is configured with FIPS mode enabled by default, but
does not include any certified binaries.


## Usage
The image is configured to enforce the use of FIPS mode by default,
independent of the host environment setup by specifying the following
environment variables:
* `OPENSSL_FIPS=1`: Initialize the OpenSSL FIPS mode
* `OPENSSL_FORCE_FIPS_MODE=1`: Set FIPS mode to enforcing independent of the host kernel
* `LIBGCRYPT_FORCE_FIPS_MODE=1`: Set FIPS mode in libgcrypt to enforcing

Below is a list of other environment variables that can be used to configure the OpenSSL library:

* `OPENSSL_ENFORCE_MODULUS_BITS=1`: Restrict the OpenSSL module to only generate
the acceptable key sizes of RSA.
## Accessing the container image

Accessing this container image requires a valid SUSE subscription. In order
to access the container image, you must login to the SUSE Registry with your credentials.
There are three ways to do that which are described below. The first two methods
leverage the system registration of your host system, while the third method
requires you to obtain the organisation SCC mirroring credentials.

### Use the system registration of your host system

If the host system you are using to build or run a container is already registered with
the correct subscription required for accessing the LTSS container images, you can use
the registration information from the host to log in to the registry.

The file `/etc/zypp/credentials.d/SCCcredentials` contains a username and a password.
These credentials allow you to access any container that is available under the
subscription of the respective host system. You can use these credentials to log
in to SUSE Registry using the following commands
(use the leading space before the echo command to avoid storing the credentials in the
shell history):

```ShellSession
set +o history
 echo PASSWORD | podman login -u USERNAME --password-stdin registry.suse.com
set -o history
```

### Use a separate SUSE Customer Center registration code

If the host system is not registered with SUSE Customer Center, you can use a valid
SUSE Customer Center registration code to log in to the registry:

```ShellSession
set +o history
 echo SCC_REGISTRATION_CODE | podman login -u "regcode" --password-stdin registry.suse.com
set -o history
```
The user parameter in this case is the verbatim string `regcode`, and
`SCC_REGISTRATION_CODE` is the actual registration code obtained from SUSE.

### Use the organization mirroring credentials

You can also use the organization mirroring credentials to log in to the
SUSE Registry:

```ShellSession
set +o history
 echo SCC_MIRRORING_PASSWORD | podman login -u "SCC_MIRRORING_USER" --password-stdin registry.suse.com
set -o history
```

These credentials give you access to all subscriptions the organization owns,
including those related to container images in the SUSE Registry.
The credentials are highly privileged and should be preferably used for
a private mirroring registry only.
## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
