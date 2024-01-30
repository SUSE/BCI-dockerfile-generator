"""Base container images maintained by the BCI generator"""

import os
import textwrap
from pathlib import Path

from bci_build.package import ALL_BASE_OS_VERSIONS
from bci_build.package import ALL_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import Arch
from bci_build.package import BuildType
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.package import Package
from bci_build.package import PackageType
from bci_build.package import SupportLevel
from bci_build.package import _build_tag_prefix
from bci_build.package import generate_disk_size_constraints

_DISABLE_GETTY_AT_TTY1_SERVICE = "systemctl disable getty@tty1.service"


def _get_os_container_package_names(os_version: OsVersion) -> tuple[str, ...]:
    if os_version == OsVersion.TUMBLEWEED:
        return ("openSUSE-release", "openSUSE-release-appliance-docker")
    if os_version == OsVersion.BASALT:
        return ("ALP-dummy-release",)
    return ("sles-release",)


MICRO_CONTAINERS = [
    OsContainer(
        name="micro",
        os_version=os_version,
        support_level=SupportLevel.L3,
        package_name="micro-image",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Micro",
        custom_description="A micro environment for containers {based_on_container}.",
        from_image=None,
        build_recipe_type=BuildType.KIWI,
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "bash",
                "ca-certificates-mozilla-prebuilt",
                # ca-certificates-mozilla-prebuilt requires /bin/cp, which is otherwise not resolved…
                "coreutils",
            )
            + (
                ()
                if os_version in (OsVersion.TUMBLEWEED, OsVersion.BASALT)
                else ("skelcd-EULA-bci",)
            )
            + _get_os_container_package_names(os_version)
        ],
        # intentionally empty
        config_sh_script="""
""",
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


INIT_CONTAINERS = [
    OsContainer(
        name="init",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Init",
        custom_description="Systemd environment for containers {based_on_container}. {podman_only}",
        package_list=["systemd", "gzip"],
        cmd=["/usr/lib/systemd/systemd"],
        extra_labels={
            "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
        },
        package_name="init-image",
        custom_end=textwrap.dedent(
            f"""
            RUN mkdir -p /etc/systemd/system.conf.d/ && \\
                printf "[Manager]\\nLogColor=no" > \\
                    /etc/systemd/system.conf.d/01-sle-bci-nocolor.conf
            RUN {_DISABLE_GETTY_AT_TTY1_SERVICE}
            HEALTHCHECK --interval=5s --timeout=5s --retries=5 CMD ["/usr/bin/systemctl", "is-active", "multi-user.target"]
            """
        ),
    )
    for os_version in ALL_BASE_OS_VERSIONS
]

# https://csrc.nist.gov/CSRC/media/projects/cryptographic-module-validation-program/documents/security-policies/140sp3991.pdf
# Chapter 9.1 Crypto Officer Guidance
_FIPS_15_SP2_ASSET_BASEURL = "https://api.opensuse.org/public/build/"
_FIPS_15_SP2_BINARIES = [
    f"SUSE:SLE-15-SP2:Update/pool/x86_64/openssl-1_1.18804/{name}-1.1.1d-11.20.1.x86_64.rpm"
    for name in ("openssl-1_1", "libopenssl1_1", "libopenssl1_1-hmac")
] + [
    f"SUSE:SLE-15-SP1:Update/pool/x86_64/libgcrypt.15117/{name}-1.8.2-8.36.1.x86_64.rpm"
    for name in ("libgcrypt20", "libgcrypt20-hmac")
]

FIPS_BASE_CONTAINERS = [
    OsContainer(
        name="base-fips",
        package_name="base-fips-image",
        exclusive_arch=[Arch.X86_64],
        os_version=os_version,
        build_recipe_type=BuildType.DOCKER,
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} FIPS-140-2",
        package_list=["fipscheck", "sles-ltss-release"],
        extra_labels={
            "usage": "This container should only be used on a FIPS enabled host (fips=1 on kernel cmdline)."
        },
        custom_end="".join(
            f"#!RemoteAssetUrl: {_FIPS_15_SP2_ASSET_BASEURL}{binary}\nCOPY {os.path.basename(binary)} .\n"
            for binary in _FIPS_15_SP2_BINARIES
        ).strip()
        + textwrap.dedent(
            f"""
            {DOCKERFILE_RUN} \\
                [ $(LC_ALL=C rpm --checksig -v *rpm | \\
                    grep -c -E "^ *V3.*key ID 39db7c82: OK") = {len(_FIPS_15_SP2_BINARIES)} ] \\
                && rpm -Uvh --oldpackage *.rpm \\
                && rm -vf *.rpm \\
                && rpmqpack | grep -E '(openssl|libgcrypt)'  | xargs zypper -n addlock
            ENV OPENSSL_FORCE_FIPS_MODE=1
            """
        ),
    )
    for os_version in (OsVersion.SP3,)
]


def _get_minimal_kwargs(os_version: OsVersion):
    package_list = [
        Package(name, pkg_type=PackageType.DELETE)
        for name in ("grep", "diffutils", "info", "fillup", "libzio1")
    ]
    package_list += [
        Package(name, pkg_type=PackageType.BOOTSTRAP)
        for name in _get_os_container_package_names(os_version)
    ]
    if os_version in (OsVersion.TUMBLEWEED, OsVersion.BASALT):
        package_list.append(Package("rpm", pkg_type=PackageType.BOOTSTRAP))
    else:
        # in SLE15, rpm still depends on Perl.
        package_list += [
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in ("rpm-ndb", "perl-base")
        ]

    kwargs = {
        "from_image": f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        "pretty_name": f"{os_version.pretty_os_version_no_dash} Minimal",
        "package_list": package_list,
    }

    return kwargs


MINIMAL_CONTAINERS = [
    OsContainer(
        name="minimal",
        **_get_minimal_kwargs(os_version),
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        package_name="minimal-image",
        os_version=os_version,
        build_recipe_type=BuildType.KIWI,
        config_sh_script=textwrap.dedent(
            """
            #==========================================
            # Remove compat-usrmerge-tools if installed
            #------------------------------------------
            if rpm -q compat-usrmerge-tools; then
                rpm -e compat-usrmerge-tools
            fi
            """
        ),
    )
    for os_version in ALL_BASE_OS_VERSIONS
]

BUSYBOX_CONTAINERS = [
    OsContainer(
        name="busybox",
        from_image=None,
        os_version=os_version,
        support_level=SupportLevel.L3,
        pretty_name=f"{os_version.pretty_os_version_no_dash} BusyBox",
        package_name="busybox-image",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        build_recipe_type=BuildType.KIWI,
        cmd=["/bin/sh"],
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in _get_os_container_package_names(os_version)
            + (
                "busybox",
                "busybox-links",
                "ca-certificates-mozilla-prebuilt",
            )
        ],
        config_sh_script=textwrap.dedent(
            """
            sed -i 's|/bin/bash|/bin/sh|' /etc/passwd
            # Will be recreated by the next rpm(1) run as root user
            rm -v /usr/lib/sysimage/rpm/Index.db
        """
        ),
        config_sh_interpreter="/bin/sh",
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


KERNEL_MODULE_CONTAINERS = []

for os_version in ALL_OS_VERSIONS - {OsVersion.TUMBLEWEED}:
    if os_version == OsVersion.BASALT:
        prefix = "basalt"
        pretty_prefix = prefix.upper()
    else:
        prefix = "sle15"
        pretty_prefix = "SLE 15"

    KERNEL_MODULE_CONTAINERS.append(
        OsContainer(
            name=f"{prefix}-kernel-module-devel",
            pretty_name=f"{pretty_prefix} Kernel Module Development",
            package_name=f"{prefix}-kernel-module-devel-image",
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            package_list=[
                "kernel-devel",
                "kernel-syms",
                "gcc",
                "kmod-compat",
                "make",
                "patch",
                "awk",
                "rpm-build",
            ]
            # tar is not in bci-base in 15.4, but we need it to unpack tarballs
            + (["tar"] if os_version == OsVersion.SP4 else []),
            extra_files={"_constraints": generate_disk_size_constraints(8)},
        )
    )


OSC_CHECKOUT = (Path(__file__).parent / "gitea-runner" / "osc_checkout").read_bytes()

GITEA_RUNNER_CONTAINER = OsContainer(
    name="gitea-runner",
    pretty_name="Gitea Action Runner",
    package_name="gitea-runner-image",
    os_version=OsVersion.TUMBLEWEED,
    is_latest=True,
    package_list=[
        "osc",
        "expect",
        "obs-service-format_spec_file",
        "obs-service-source_validator",
        "typescript",
        "git",
        *_get_os_container_package_names(OsVersion.TUMBLEWEED),
    ],
    extra_files={"osc_checkout": OSC_CHECKOUT},
    custom_end=f"""COPY osc_checkout /usr/bin/osc_checkout
{DOCKERFILE_RUN} chmod +x /usr/bin/osc_checkout""",
)
