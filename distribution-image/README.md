# SLE OCI Container Registry (Distribution): Suitable for running a local OCI registry
[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description
This container image allows to run a local OCI registry.


## Usage
Before you start the container,
you need to create a `config.yml` with the following content:

```yaml
---
version: 0.1
log:
  level: info
storage:
  filesystem:
    rootdirectory: /var/lib/docker-registry
http:
  addr: 0.0.0.0:5000
```

You can also create an empty directory for storing the images outside the container:

```bash
mkdir -p /var/lib/docker-registry
```

Then you can start the container with the following command:

```bash
podman run -d --restart=always -p 5000:5000 -v /path/to/config.yml:/etc/registry/config.yml \
  -v /var/lib/docker-registry:/var/lib/docker-registry --name registry registry.suse.com/suse/registry:%%registry_version%%-%RELEASE%
```

The registry is available at `http://localhost:5000`. To keep the registry running after a reboot, create a systemd service as follows:

```bash
sudo podman generate systemd registry > /etc/systemd/system/registry.service
sudo systemctl enable --now registry
```

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.