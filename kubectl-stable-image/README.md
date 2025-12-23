# kubectl Container Image

[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

Kubectl is a command line tool for communicating with a Kubernetes cluster's control plane, using the Kubernetes API.

## How to use this Container Image

To run commands inside the container for the current cluster for which the kubeconfig is available in `/root/.kube.config`:

```ShellSession
podman run --rm --name kubectl\
      registry.suse.com/suse/kubectl:1.35 get nodes
```

To pass configuration of a remote cluster to the container:

```ShellSession
podman run --rm --name kubectl\
      -v /localpath/to/kubeconfig:/root/.kube/config:Z
      registry.suse.com/suse/kubectl:1.35 get nodes
```

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.