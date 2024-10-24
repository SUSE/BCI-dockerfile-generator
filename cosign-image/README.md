# SLE cosign
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description
Cosign aims to make signatures invisible infrastructure.

Cosign supports:

* "Keyless signing" with the Sigstore public good Fulcio certificate authority and Rekor transparency log (default)
* Hardware and KMS signing
* Signing with a cosign generated encrypted private/public keypair
* Container Signing, Verification and Storage in an OCI registry.
* Bring-your-own PKI


## Usage

### ### Verify a container

To verify the image, you'll need to pass in the expected certificate subject
and certificate issuer via the `--certificate-identity` and
`--certificate-oidc-issuer` flags:

```
podman run registry.suse.com/suse/cosign:2.2 verify $IMAGE --certificate-identity=$IDENTITY --certificate-oidc-issuer=$OIDC_ISSUER
```

You can also pass in a regex for the certificate identity and issuer flags,
`--certificate-identity-regexp` and `--certificate-oidc-issuer-regexp`.

### Verify a container against a public key

This command returns `0` if *at least one* `cosign` formatted signature for
the image is found matching the public key. See the detailed usage below for
information and caveats on other signature formats.

Any valid payloads are printed to stdout, in json format. Note that these
signed payloads include the digest of the container image, which is how we
can be sure these "detached" signatures cover the correct image.

```shell
$ podman run registry.suse.com/suse/cosign:2.2 verify --key cosign.pub $IMAGE_URI:1h
The following checks were performed on these signatures:
  - The cosign claims were validated
  - The signatures were verified against the specified public key
{"Critical":{"Identity":{"docker-reference":""},"Image":{"Docker-manifest-digest":"sha256:87ef60f558bad79beea6425a3b28989f01dd417164150ab3baab98dcbf04def8"},"Type":"cosign container image signature"},"Optional":null}

For more use cases and information, please check out the
[cosign README.md](https://github.com/sigstore/cosign/blob/main/README.md).

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
