# SLE OCI Container Registry (Distribution): Suitable for running a local OCI registry

![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)

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

The build recipe and this documentation is licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
