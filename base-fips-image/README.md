
# The SUSE Linux Enterprise FIPS-140-3 container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
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
## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
