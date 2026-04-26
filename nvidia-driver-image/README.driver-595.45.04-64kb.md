# NVIDIA Driver 595.45.04 Container Image
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The NVIDIA Driver container image provides NVIDIA GPU drivers in a
containerized environment. This image is based on
SUSE Linux Enterprise Server and includes both the
open-source and proprietary NVIDIA kernel modules 595.45.04, along with the necessary
user-space tools.

It is providing [precompiled binaries](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/precompiled-drivers.html) for the NVIDIA GPU Operator or for manual
driver deployment on container hosts, allowing for faster deployment.

## Usage

To deploy this container image, use the NVIDIA GPU Operator Helm chart version 26.3.1 or later, following [these steps](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html#procedure).

Add the arguments `--set driver.repository=registry.suse.com/third-party/nvidia --set driver.usePrecompiled=true` and `--set driver.version=<driver-branch>` to the `helm install` command. `<driver-branch>` is the major version of the GPU driver (such as `595`, `590` or `580`).

For k3s or RKE2 cl, add `--set toolkit.env[0].name=CONTAINERD_SOCKET --set toolkit.env[0].value=/run/k3s/containerd/containerd.sock` when [Node Resource Interface (NRI) plugin](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/cdi.html#nri-plugin) is not enabled.

As an example:
```ShellSession
helm install --wait gpu-operator \
     -n gpu-operator --create-namespace \
     nvidia/gpu-operator \
     --version=v26.3.1 \
     --set driver.repository=registry.suse.com/third-party/nvidia \
     --set driver.usePrecompiled=true \
     --set driver.version="<driver-branch> \
     --set toolkit.env[0].name=CONTAINERD_SOCKET \
     --set toolkit.env[0].value=/run/k3s/containerd/containerd.sock"
```

## Licensing

`SPDX-License-Identifier: NVIDIA DEEP LEARNING CONTAINER LICENSE`

This documentation and the build recipe are licensed as NVIDIA DEEP LEARNING CONTAINER LICENSE.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
