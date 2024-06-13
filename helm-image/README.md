# Kubernetes Package Manager container image


[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)


## Description

[Helm](https://helm.sh/) is a tool for managing [Kubernetes](https://kubernetes.io/) charts, which are packages of pre-configured Kubernetes resources. This container image simplifies the deployment and use of Helm by packaging it into a ready-to-use container.


## Usage

To run Helm, use the following comamand:

```ShellSession
# podman run --rm -it  registry.suse.com/suse/helm:%%helm_version%% <helm-sub-command>

podman run --rm -it registry.suse.com/suse/helm:%%helm_version%% version
```

Refer to the full list of Helm commands, flags and environment variables, in the [official Helm documentation](https://helm.sh/docs/helm/helm/).

For a comprehensive guide on getting started with Helm, refer to the [official Helm tutorial](https://helm.sh/docs/chart_template_guide/getting_started/).

### Connecting Helm container to the Host's Kubernetes Cluster

To interact with a Kubernetes cluster running on the host, mount the Kubernetes configuration file (`kubeconfig`) into the container (use `--net=host` flag to allow container to use host’s network):

```ShellSession
podman run --rm -it --net=host -v /path/to/kubeconfig:/root/.kube/config registry.suse.com/suse/helm:%%helm_version%%
```

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.