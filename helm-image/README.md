# Kubernetes Package Manager container image

[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)


## Description

[Helm](https://helm.sh/) is a tool for managing [Kubernetes](https://kubernetes.io/) charts, which are packages of pre-configured Kubernetes resources. This container image simplifies the deployment and use of Helm by packaging it into a ready-to-use container.


## Usage

To run Helm, use the following command:

```ShellSession
$ podman run --rm -it  registry.suse.com/suse/helm:3.13 <helm-sub-command>
```

For instance, to display the Helm version, run:
```ShellSession
$ podman run --rm -it registry.suse.com/suse/helm:3.13 version --template='{{.Version}}'
v3.13
```

Refer to the full list of Helm commands, flags and environment variables, in the [official Helm documentation](https://helm.sh/docs/helm/helm/).

For a comprehensive guide on getting started with Helm, refer to the [official Helm tutorial](https://helm.sh/docs/chart_template_guide/getting_started/).

### Connecting Helm container to the Host's Kubernetes Cluster


To interact with a Kubernetes cluster, mount the Kubernetes configuration file (`kubeconfig`) from the container host into the container (use the `--net=host` flag to allow the container to use the host’s network):

```ShellSession
$ podman run --rm -it --net=host -v /path/to/kubeconfig:/root/.kube/config:Z registry.suse.com/suse/helm:3.13
```

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.