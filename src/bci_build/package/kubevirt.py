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

KUBEVIRT_EXCLUSIVE_ARCH = [Arch.AARCH64, Arch.X86_64]
_KUBEVIRT_VERSIONS = (
    ("1.8", OsVersion.SL16_0),
    ("1.8", OsVersion.SL16_1),
    ("1.8", OsVersion.TUMBLEWEED),
    ("1.9", OsVersion.TUMBLEWEED),
)


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


def _kubevirt_pkg(kubevirt_version: str) -> str:
    """Get the KubeVirt package name for a given Kubevirt version."""
    return f"kubevirt{kubevirt_version}"


def _kubevirt_dir(kubevirt_version: str) -> str:
    """Get the KubeVirt directory name for a given Kubevirt version."""
    return f"kube-virt-{kubevirt_version}"


def _get_kubevirt_kwargs(
    service: str,
    kubevirt_version: str,
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
        f"{_kubevirt_pkg(kubevirt_version)}-virt-{service}"
        if custom_service_pkg_name is None
        else custom_service_pkg_name
    )
    kubevirt_pkg_version = get_pkg_version(_kubevirt_pkg(kubevirt_version), os_version)
    kubevirt_version_re = "%%kubevirt_ver%%"
    return {
        "name": f"virt-{service}",
        "pretty_name": f"KubeVirt virt-{service}",
        "package_name": f"kubevirt-{kubevirt_version}-image",
        "license": "Apache-2.0",
        "os_version": os_version,
        "tag_version": format_version(kubevirt_pkg_version, ParseVersion.MINOR),
        "version": kubevirt_version_re,
        "replacements_via_service": [
            Replacement(
                kubevirt_version_re,
                package_name=_kubevirt_pkg(kubevirt_version),
                parse_version=ParseVersion.PATCH,
            )
        ],
        "is_latest": (
            os_version in CAN_BE_LATEST_OS_VERSION and os_version.is_tumbleweed
        ),
        "build_flavor": service,
        "version_in_uid": True,
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


def _get_libguestfs_kwargs(kubevirt_version: str, os_version: OsVersion) -> dict:
    """Generate kwargs for the libguestfs-tools container.

    It deviates from the virt-* services in two ways: it is published without
    the ``virt-`` prefix (matching :file:`suse/sles/15.7/libguestfs-tools`),
    and its builder stage does double duty: supermin can only compose the
    guest appliance from a fully installed system, so the appliance is baked
    in the builder's own root — the kernel, the devel tools and the harvested
    userland never reach the bci-micro based target, which receives only the
    finished appliance and the runtime closure of the content package.
    """
    kwargs = _get_kubevirt_kwargs(
        "libguestfs-tools",
        kubevirt_version,
        os_version,
        custom_service_pkg_name=f"{_kubevirt_pkg(kubevirt_version)}-libguestfs-tools",
    )
    kwargs["name"] = "libguestfs-tools"
    kwargs["pretty_name"] = "KubeVirt libguestfs-tools"
    kwargs["build_stage_custom_end"] += textwrap.dedent(f"""
        # everything supermin harvests must be installed here, not in /target
        {DOCKERFILE_RUN} zypper -n install --no-recommends btrfsprogs cpio cryptsetup \\
        dosfstools e2fsprogs gptfdisk guestfs-tools jfsutils kernel-kvmsmall ldmtool \\
        libguestfs libguestfs-appliance libguestfs-devel libguestfs-winsupport mdadm \\
        parted qemu-tools qemu-x86 supermin xfsprogs xorriso zstd

        # build once at image build so pods do not run supermin at startup;
        # store the root as compressed qcow2 because image layers do not
        # preserve sparseness
        {DOCKERFILE_RUN} mkdir -p /usr/local/lib/guestfs/appliance && \\
            cd /usr/local/lib/guestfs/appliance && \\
            LIBGUESTFS_BACKEND=direct LIBGUESTFS_DEBUG=1 libguestfs-make-fixed-appliance . && \\
            qemu-img convert -c -O qcow2 root root.qcow2 && \\
            mv root.qcow2 root && \\
            rm -rf /var/tmp/.guestfs-*
        """)

    kwargs["custom_end"] += textwrap.dedent(f"""
        COPY --from=builder /usr/local/lib/guestfs/appliance /usr/local/lib/guestfs/appliance
        {DOCKERFILE_RUN} install -p -m 0755 /usr/share/{_kubevirt_dir(kubevirt_version)}/libguestfs-tools/entrypoint.sh /entrypoint.sh

        # cross-stage COPY leaves the home dir root-owned
        {DOCKERFILE_RUN} chown -R 1001:users /home/virt-libguestfs-tools
        """)
    return kwargs


KUBEVIRT_CONTAINERS = (
    [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("api", kubevirt_version, os_version),
            package_list=sorted(
                [f"{_kubevirt_pkg(kubevirt_version)}-virt-api", "shadow"]
            ),
            entrypoint=["/usr/bin/virt-api"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("controller", kubevirt_version, os_version),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-controller",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/virt-controller"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("exportproxy", kubevirt_version, os_version),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-exportproxy",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/virt-exportproxy"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "exportserver", kubevirt_version, os_version, user="107"
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-exportserver",
                    "system-user-qemu",
                    "tar",
                ]
            ),
            entrypoint=["/usr/bin/virt-exportserver"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "handler", kubevirt_version, os_version, user="0", custom_end=False
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-handler",
                    "curl",
                    "iproute2",
                    f"{_kubevirt_pkg(kubevirt_version)}-container-disk",
                    "nftables",
                    # sysctl: node-labeller probes it to decide whether the node
                    # can run realtime workloads; without it every virt-handler
                    # logs "failed to identify if a node is capable of running
                    # realtime workloads" and the label is never set. procps
                    # also provides the pgrep the e2e reporter execs here.
                    "procps",
                    "qemu-img",
                    "system-user-qemu",
                    "tar",
                    "util-linux-systemd",
                ]
            ),
            entrypoint=["/usr/bin/virt-handler"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "launcher", kubevirt_version, os_version, user="0", custom_end=False
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-launcher",
                    f"{_kubevirt_pkg(kubevirt_version)}-container-disk",
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
                    install -m 0644 /usr/share/{_kubevirt_dir(kubevirt_version)}/virt-launcher/virtqemud.conf /etc/libvirt/virtqemud.conf && \\
                    install -m 0644 /usr/share/{_kubevirt_dir(kubevirt_version)}/virt-launcher/qemu.conf /etc/libvirt/qemu.conf && \\
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
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("operator", kubevirt_version, os_version),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-operator",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/virt-operator"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "synchronization-controller", kubevirt_version, os_version
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-virt-synchronization-controller",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/virt-synchronization-controller"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs(
                "pr-helper",
                kubevirt_version,
                os_version,
                user="0",
                custom_end=False,
                custom_service_pkg_name=f"{_kubevirt_pkg(kubevirt_version)}-pr-helper-conf",
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-pr-helper-conf",
                    "qemu-pr-helper",
                ]
            ),
            # virt-operator runs this container as `/entrypoint.sh` (see
            # RenderPrHelperContainer): the script symlinks the multipath
            # socket, then execs qemu-pr-helper. Shipping only the binary
            # leaves the container unable to start at all.
            entrypoint=["/entrypoint.sh"],
            custom_end=(
                f"{DOCKERFILE_RUN} cp -f /usr/share/{_kubevirt_dir(kubevirt_version)}/pr-helper/multipath.conf /etc/\n"
                f"{DOCKERFILE_RUN} install -p -m 0755 /usr/share/{_kubevirt_dir(kubevirt_version)}/pr-helper/entrypoint.sh /entrypoint.sh"
            ),
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **(
                _get_kubevirt_kwargs(
                    "sidecar-shim",
                    kubevirt_version,
                    os_version,
                    custom_service_pkg_name=f"{_kubevirt_pkg(kubevirt_version)}-sidecar-shim",
                )
                # virt-controller resolves the default hook-sidecar image as
                # <registry>/sidecar-shim:<version> — no virt- prefix
                | {"name": "sidecar-shim", "pretty_name": "KubeVirt sidecar-shim"}
            ),
            package_list=sorted(
                [
                    f"{_kubevirt_pkg(kubevirt_version)}-sidecar-shim",
                    # user hook scripts run inside this image; upstream ships
                    # python3 in it for them
                    "python3",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/sidecar-shim"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_libguestfs_kwargs(kubevirt_version, os_version),
            package_list=sorted(
                [
                    # the content package: entrypoint + the runtime closure of
                    # the image as Requires (mirrors upstream's rpm tree) —
                    # everything else the image needs at runtime is pulled in
                    # by RPM dependency resolution
                    f"{_kubevirt_pkg(kubevirt_version)}-libguestfs-tools",
                    # the entrypoint drops the user into an interactive shell;
                    # bci-micro ships neither bash nor login tooling
                    "bash",
                    "shadow",
                ]
            ),
            entrypoint=["/entrypoint.sh"],
        )
        for kubevirt_version, os_version in _KUBEVIRT_VERSIONS
    ]
)

KUBEVIRT_CRATE = ContainerCrate(KUBEVIRT_CONTAINERS)
