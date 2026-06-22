# NVIDIA Driver 580.159.04 Container Image
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The NVIDIA Driver container image provides NVIDIA GPU drivers in a
containerized environment. This image is based on
SUSE Linux Enterprise Server and includes both the
open-source and proprietary NVIDIA kernel modules 580.159.04, along with the necessary
user-space tools.

It provides [precompiled binaries](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/precompiled-drivers.html) for the NVIDIA GPU Operator or for manual
driver deployment on container hosts, allowing for faster deployment.

## Usage

To deploy this container image, use the NVIDIA GPU Operator Helm chart version 26.3.1 or later, following [these steps](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html#procedure).

Add the arguments `--set driver.repository=registry.suse.com/third-party/nvidia`, `--set driver.usePrecompiled=true`, and `--set driver.version=<driver-branch>` to the `helm install` command. Replace `<driver-branch>` with the major version of the GPU driver (such as `595`, `590`, or `580`).

For K3s or RKE2, the [Node Resource Interface (NRI) plug-in](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/cdi.html#nri-plugin) should be enabled by using `--set cdi.nriPluginEnabled=true`.

Example:
```ShellSession
helm install --wait gpu-operator \
     -n gpu-operator --create-namespace \
     nvidia/gpu-operator \
     --version=v26.3.1 \
     --set cdi.nriPluginEnabled=true \
     --set driver.repository=registry.suse.com/third-party/nvidia \
     --set driver.usePrecompiled=true \
     --set driver.version=<driver-branch>
```

Secure Boot must be disabled on the host to allow the container to load kernel modules.

This driver container image requires the full `kernel-default` or `kernel-default-64kb` RPM package to be installed on the host. Using the `kernel-default-base` RPM package is not supported, and will cause the driver container to fail to initialize properly.

## Licensing

`SPDX-License-Identifier: NVIDIA DEEP LEARNING CONTAINER LICENSE`

This documentation and the build recipe are licensed as NVIDIA DEEP LEARNING CONTAINER LICENSE.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
