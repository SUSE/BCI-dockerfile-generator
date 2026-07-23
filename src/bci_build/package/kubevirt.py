"""Common Definitions for the KubeVirt containers."""

import textwrap

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.registry import SUSERegistry
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

KUBEVIRT_EXCLUSIVE_ARCH = [Arch.X86_64]
_KUBEVIRT_VERSIONS = (OsVersion.SL16_0, OsVersion.SL16_1, OsVersion.TUMBLEWEED)


class KubeVirtRegistrySL160(SUSERegistry):
    """Registry for KubeVirt containers."""

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        if not is_application:
            raise RuntimeError("KubeVirt containers must be Application Containers")
        return "suse/sles/16.0"


class KubeVirtRegistrySL161(SUSERegistry):
    """Registry for KubeVirt containers."""

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        if not is_application:
            raise RuntimeError("KubeVirt containers must be Application Containers")
        return "suse/sles/16.1"


def _kubevirt_pkg(os_version: OsVersion) -> str:
    """Get the KubeVirt package name for a given OS version."""
    return "kubevirt" if os_version == OsVersion.SP7 else "kubevirt1.8"


def _kubevirt_dir(os_version: OsVersion) -> str:
    """Get the KubeVirt directory name for a given OS version."""
    return "kube-virt" if os_version == OsVersion.SP7 else "kube-virt-1.8"


def _get_kubevirt_kwargs(
    service: str,
    os_version: OsVersion,
    *,
    user=None,
    custom_end=True,
    custom_service_pkg_name=None,
) -> dict:
    """Generate common kwargs for KubeVirt containers."""

    if user is None:
        user = "1001"
    service_pkg_name = (
        f"{_kubevirt_pkg(os_version)}-virt-{service}"
        if custom_service_pkg_name is None
        else custom_service_pkg_name
    )
    kubevirt_version = get_pkg_version(_kubevirt_pkg(os_version), os_version)
    kubevirt_version_re = "%%kubevirt_ver%%"
    return {
        "name": f"virt-{service}",
        "pretty_name": f"KubeVirt virt-{service}",
        "package_name": (
            "kubevirt-1.8-image"
            if os_version not in (OsVersion.SP7,)
            else "kubevirt-image"
        ),
        "license": "Apache-2.0",
        "os_version": os_version,
        "tag_version": format_version(kubevirt_version, ParseVersion.MINOR),
        "version": kubevirt_version_re,
        "replacements_via_service": [
            Replacement(
                kubevirt_version_re,
                package_name=_kubevirt_pkg(os_version),
                parse_version=ParseVersion.PATCH,
            )
        ],
        "is_singleton_image": True,
        "is_latest": (
            os_version in CAN_BE_LATEST_OS_VERSION and os_version.is_tumbleweed
        ),
        "build_flavor": service,
        "version_in_uid": False,
        "use_build_flavor_in_tag": False,
        "entrypoint_user": user if user != "0" else None,
        "exclusive_arch": KUBEVIRT_EXCLUSIVE_ARCH,
        "support_level": SupportLevel.L3,
        "_publish_registry": (
            KubeVirtRegistrySL160()
            if os_version == OsVersion.SL16_0
            else KubeVirtRegistrySL161()
            if os_version == OsVersion.SL16_1
            else None
        ),
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "build_stage_custom_end": (
            generate_package_version_check(
                service_pkg_name, kubevirt_version, use_target=True
            )
            + (
                f"\n{DOCKERFILE_RUN} if rpm --root /target -q compat-usrmerge-tools; then rpm --root /target -e compat-usrmerge-tools; fi\n"
            )
            + (
                textwrap.dedent(f"""
            {DOCKERFILE_RUN} useradd -u {user} --create-home -s /bin/bash virt-{service}
            """)
                if user != "0"
                else ""
            )
        ),
    } | (
        {
            "custom_end": textwrap.dedent(f"""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/virt-{service} /home/virt-{service}
            """),
        }
        if custom_end
        else {}
    )


KUBEVIRT_CONTAINERS = (
    [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("api", os_version),
            package_list=sorted([f"{_kubevirt_pkg(os_version)}-virt-api", "shadow"]),
            entrypoint=["/usr/bin/virt-api"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("controller", os_version),
            package_list=sorted(
                [f"{_kubevirt_pkg(os_version)}-virt-controller", "shadow"]
            ),
            entrypoint=["/usr/bin/virt-controller"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("exportproxy", os_version),
            package_list=sorted(
                [f"{_kubevirt_pkg(os_version)}-virt-exportproxy", "shadow"]
            ),
            entrypoint=["/usr/bin/virt-exportproxy"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("exportserver", os_version, user="107"),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(os_version)}-virt-exportserver",
                    "system-user-qemu",
                    "tar",
                ]
            ),
            entrypoint=["/usr/bin/virt-exportserver"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("handler", os_version, user="0", custom_end=False),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(os_version)}-virt-handler",
                    "curl",
                    "iproute2",
                    f"{_kubevirt_pkg(os_version)}-container-disk",
                    "nftables",
                    "qemu-img",
                    "system-user-qemu",
                    "tar",
                    "util-linux-systemd",
                ]
            ),
            entrypoint=["/usr/bin/virt-handler"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("launcher", os_version, user="0", custom_end=False),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(os_version)}-virt-launcher",
                    f"{_kubevirt_pkg(os_version)}-container-disk",
                    "libvirt-daemon-driver-qemu",
                    "libvirt-client",
                    "qemu-hw-usb-host",
                    "qemu-hw-usb-redirect",
                    "virtiofsd",
                    "passt",
                    "nftables",
                    "tar",
                    "xorriso",
                    "qemu-ovmf-x86_64",
                    "libcap-progs",
                    "shadow",
                ]
                + (["ncat"] if os_version != OsVersion.TUMBLEWEED else [])
                + (["usbredir"] if os_version == OsVersion.TUMBLEWEED else [])
            ),
            entrypoint=["/usr/bin/virt-launcher-monitor"],
            custom_end=textwrap.dedent(f"""
                {DOCKERFILE_RUN} rm -f /var/run && ln -s ../run /var/run && \\
                    install -m 0644 /usr/share/{_kubevirt_dir(os_version)}/virt-launcher/virtqemud.conf /etc/libvirt/virtqemud.conf && \\
                    install -m 0644 /usr/share/{_kubevirt_dir(os_version)}/virt-launcher/qemu.conf /etc/libvirt/qemu.conf && \\
                    chmod 0755 /etc/libvirt && \\
                    setcap 'cap_net_bind_service=+ep' /usr/bin/virt-launcher-monitor
                {DOCKERFILE_RUN} install -d -m 0755 /usr/share/edk2/ovmf && \\
                    ln -s /usr/share/qemu/ovmf-x86_64-4m-code.bin     /usr/share/edk2/ovmf/OVMF_CODE.fd && \\
                    ln -s /usr/share/qemu/ovmf-x86_64-4m-vars.bin     /usr/share/edk2/ovmf/OVMF_VARS.fd && \\
                    ln -s /usr/share/qemu/ovmf-x86_64-smm-ms-code.bin /usr/share/edk2/ovmf/OVMF_CODE.secboot.fd && \\
                    ln -s /usr/share/qemu/ovmf-x86_64-smm-ms-vars.bin /usr/share/edk2/ovmf/OVMF_VARS.secboot.fd && \\
                    ln -s /usr/share/qemu/ovmf-x86_64-sev.bin         /usr/share/edk2/ovmf/OVMF_CODE.cc.fd && \\
                    ln -s edk2/ovmf /usr/share/OVMF
                ENV MALLOC_ARENA_MAX=1
                """),
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("operator", os_version),
            package_list=sorted(
                [f"{_kubevirt_pkg(os_version)}-virt-operator", "shadow"]
            ),
            entrypoint=["/usr/bin/virt-operator"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("synchronization-controller", os_version),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(os_version)}-virt-synchronization-controller",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/virt-synchronization-controller"],
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "pr-helper",
                os_version,
                user="0",
                custom_end=False,
                custom_service_pkg_name=f"{_kubevirt_pkg(os_version)}-pr-helper-conf",
            ),
            package_list=sorted(
                [f"{_kubevirt_pkg(os_version)}-pr-helper-conf", "qemu-pr-helper"]
            ),
            entrypoint=["/usr/bin/qemu-pr-helper"],
            custom_end=f"{DOCKERFILE_RUN} cp -f /usr/share/{_kubevirt_dir(os_version)}/pr-helper/multipath.conf /etc/",
        )
        for os_version in _KUBEVIRT_VERSIONS
    ]
)

KUBEVIRT_CRATE = ContainerCrate(KUBEVIRT_CONTAINERS)
