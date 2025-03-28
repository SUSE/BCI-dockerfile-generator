# kubectl Container Image

![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

Kubectl is a command line tool for communicating with a Kubernetes cluster's control plane, using the Kubernetes API.

## How to use this Container Image

To run commands inside the container for the current cluster for which the kubeconfig is available in `/root/.kube.config`:

```ShellSession
podman run --rm --name kubectl\
      registry.suse.com/suse/kubectl:1.31 get nodes
```

To pass configuration of a remote cluster to the container:

```ShellSession
podman run --rm --name kubectl\
      -v /localpath/to/kubeconfig:/root/.kube/config:Z
      registry.suse.com/suse/kubectl:1.31 get nodes
```

## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
