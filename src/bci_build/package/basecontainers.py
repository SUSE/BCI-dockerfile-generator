"""Base container images maintained by the BCI generator"""

import datetime
import os
import textwrap
from pathlib import Path

from bci_build.package import ALL_BASE_OS_VERSIONS
from bci_build.package import ALL_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import _SUPPORTED_UNTIL_SLE
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


MICRO_CONTAINERS = [
    OsContainer(
        name="micro",
        os_version=os_version,
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        package_name="micro-image",
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
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
            + os_version.eula_package_names
            + os_version.release_package_names
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
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Init",
        custom_description="Systemd environment for containers {based_on_container}. {podman_only}",
        package_list=["systemd", "gzip"],
        cmd=["/usr/lib/systemd/systemd"],
        extra_labels={
            "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
        },
        package_name="init-image",
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
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

_FIPS_ASSET_BASEURL = "https://api.opensuse.org/public/build/"

# https://csrc.nist.gov/CSRC/media/projects/cryptographic-module-validation-program/documents/security-policies/140sp3991.pdf
# Chapter 9.1 Crypto Officer Guidance
_FIPS_15_SP2_BINARIES: list[str] = [
    f"SUSE:SLE-15-SP2:Update/pool/x86_64/openssl-1_1.18804/{name}-1.1.1d-11.20.1.x86_64.rpm"
    for name in ("openssl-1_1", "libopenssl1_1", "libopenssl1_1-hmac")
] + [
    f"SUSE:SLE-15-SP1:Update/pool/x86_64/libgcrypt.15117/{name}-1.8.2-8.36.1.x86_64.rpm"
    for name in ("libgcrypt20", "libgcrypt20-hmac")
]

# submitted, not yet certified
_FIPS_15_SP4_BINARIES: list[str] = [
    f"SUSE:SLE-15-SP4:Update/pool/x86_64/openssl-1_1.28168/{name}-1.1.1l-150400.7.28.1.x86_64.rpm"
    for name in ("openssl-1_1", "libopenssl1_1", "libopenssl1_1-hmac")
] + [
    f"SUSE:SLE-15-SP4:Update/pool/x86_64/libgcrypt.28151/{name}-1.9.4-150400.6.8.1.x86_64.rpm"
    for name in ("libgcrypt20", "libgcrypt20-hmac")
]


def _get_fips_base_custom_end(os_version: OsVersion) -> str:
    bins: list[str] = []
    custom_set_fips_mode: str = (
        f"{DOCKERFILE_RUN} update-crypto-policies --no-reload --set FIPS\n"
    )
    match os_version:
        case OsVersion.SP3:
            bins = _FIPS_15_SP2_BINARIES
        case OsVersion.SP4:
            bins = _FIPS_15_SP4_BINARIES
        case OsVersion.SP5 | OsVersion.SP6:
            pass
        case _:
            raise NotImplementedError(f"Unsupported os_version: {os_version}")

    custom_install_bins: str = textwrap.dedent(
        f"""
            {DOCKERFILE_RUN} \\
                [ $(LC_ALL=C rpm --checksig -v *rpm | \\
                    grep -c -E "^ *V3.*key ID 39db7c82: OK") = {len(bins)} ] \\
                && rpm -Uvh --oldpackage --force *.rpm \\
                && rm -vf *.rpm \\
                && rpmqpack | grep -E '(openssl|libgcrypt)' | xargs zypper -n addlock\n"""
    )

    return (
        "".join(
            f"#!RemoteAssetUrl: {_FIPS_ASSET_BASEURL}{binary}\nCOPY {os.path.basename(binary)} .\n"
            for binary in bins
        ).strip()
        + (custom_install_bins if bins else "")
        + (custom_set_fips_mode if os_version not in (OsVersion.SP3,) else "")
    )


def _get_fips_pretty_name(os_version: OsVersion) -> str:
    match os_version:
        case OsVersion.SP3:
            return f"{os_version.pretty_os_version_no_dash} FIPS-140-2"
        case OsVersion.SP4 | OsVersion.SP5 | OsVersion.SP6:
            return f"{os_version.pretty_os_version_no_dash} FIPS-140-3"
        case _:
            raise NotImplementedError(f"Unsupported os_version: {os_version}")


def _get_supported_until_fips(os_version: OsVersion) -> datetime.date:
    """Returns the end of LTSS for images under LTSS, otherwise end of general support if known"""
    match os_version:
        case OsVersion.SP3:
            return datetime.date(2025, 12, 31)
        case OsVersion.SP4:
            return datetime.date(2026, 12, 31)
        case _:
            return _SUPPORTED_UNTIL_SLE.get(os_version)


FIPS_BASE_CONTAINERS = [
    OsContainer(
        name="base-fips",
        package_name="base-fips-image",
        exclusive_arch=[Arch.X86_64],
        os_version=os_version,
        build_recipe_type=BuildType.DOCKER,
        support_level=SupportLevel.L3,
        supported_until=_get_supported_until_fips(os_version),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=_get_fips_pretty_name(os_version),
        package_list=[*os_version.release_package_names]
        + (
            ["fipscheck"]
            if os_version == OsVersion.SP3
            else ["crypto-policies-scripts"]
        ),
        extra_labels={
            "usage": "This container should only be used on a FIPS enabled host (fips=1 on kernel cmdline)."
        },
        custom_end=_get_fips_base_custom_end(os_version)
        + textwrap.dedent(
            """
            ENV OPENSSL_FIPS=1
            ENV OPENSSL_FORCE_FIPS_MODE=1
            ENV LIBGCRYPT_FORCE_FIPS_MODE=1
            """
        ),
    )
    for os_version in (OsVersion.SP3, OsVersion.SP4, OsVersion.SP5, OsVersion.SP6)
]


def _get_minimal_kwargs(os_version: OsVersion):
    package_list = [
        Package(name, pkg_type=PackageType.DELETE)
        for name in ("grep", "diffutils", "info", "fillup", "libzio1")
    ]
    # the last user of libpcre1 on SP6 is grep which we deinstall above
    if os_version in (OsVersion.SP6,):
        package_list.append(Package("libpcre1", pkg_type=PackageType.DELETE))

    package_list += [
        Package(name, pkg_type=PackageType.BOOTSTRAP)
        for name in os_version.release_package_names
    ]
    if os_version in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0):
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
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        package_name="minimal-image",
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
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
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        pretty_name=f"{os_version.pretty_os_version_no_dash} BusyBox",
        package_name="busybox-image",
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        build_recipe_type=BuildType.KIWI,
        cmd=["/bin/sh"],
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                os_version.release_package_names
                + (
                    "busybox",
                    "busybox-links",
                    "ca-certificates-mozilla-prebuilt",
                )
                + os_version.eula_package_names
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
    if os_version == OsVersion.SLE16_0:
        prefix = "basalt"
        pretty_prefix = prefix.upper()
    else:
        prefix = "sle15"
        pretty_prefix = "SLE 15"

    KERNEL_MODULE_CONTAINERS.append(
        OsContainer(
            name=f"{prefix}-kernel-module-devel",
            pretty_name=f"{pretty_prefix} Kernel module development",
            package_name=f"{prefix}-kernel-module-devel-image",
            logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
            os_version=os_version,
            supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            package_list=[
                "kernel-devel",
                "kernel-syms",
                "gcc",
                "kmod",
                "make",
                "patch",
                "gawk",
                "rpm-build",
                *os_version.release_package_names,
            ]
            # tar is not in bci-base in 15.4, but we need it to unpack tarballs
            + (["tar"] if os_version == OsVersion.SP4 else []),
            extra_files={"_constraints": generate_disk_size_constraints(8)},
        )
    )


OSC_CHECKOUT = (Path(__file__).parent / "gitea-runner" / "osc_checkout").read_bytes()

GITEA_RUNNER_CONTAINER = OsContainer(
    name="gitea-runner",
    pretty_name="Gitea action runner",
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
        *OsVersion.TUMBLEWEED.release_package_names,
    ],
    extra_files={"osc_checkout": OSC_CHECKOUT},
    custom_end=f"""COPY osc_checkout /usr/bin/osc_checkout
{DOCKERFILE_RUN} chmod +x /usr/bin/osc_checkout""",
)
