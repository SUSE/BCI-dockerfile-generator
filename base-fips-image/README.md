
# The SUSE Linux Enterprise FIPS-140-3 container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description


This base container image is configured with FIPS mode enabled by default, but
**does not** include any certified binaries.


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

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
