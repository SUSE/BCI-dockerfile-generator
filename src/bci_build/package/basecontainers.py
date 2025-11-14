"""Base container images maintained by the BCI generator"""

import datetime
import os
import textwrap
from pathlib import Path

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_BASE_OS_VERSIONS
from bci_build.os_version import ALL_OS_LTSS_VERSIONS
from bci_build.os_version import ALL_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_BASE_OS_VERSION
from bci_build.os_version import CAN_BE_SAC_VERSION
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import generate_disk_size_constraints

_DISABLE_GETTY_AT_TTY1_SERVICE = "systemctl disable getty@tty1.service"


def _get_micro_package_list(os_version: OsVersion) -> list[Package]:
    return [
        Package(name, pkg_type=PackageType.BOOTSTRAP)
        for name in (
            "bash",
            "ca-certificates-mozilla-prebuilt",
            # ca-certificates-mozilla-prebuilt requires /bin/cp, which is otherwise not resolved…
            "coreutils",
        )
        + os_version.eula_package_names
        + os_version.release_package_names
    ]


MICRO_CONTAINERS = [
    OsContainer(
        name="micro",
        os_version=os_version,
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
        is_singleton_image=(
            # preserve backwards compatibility on already released distributions
            not os_version.is_sle15
        ),
        pretty_name=f"{os_version.pretty_os_version_no_dash} Micro",
        custom_description="A micro environment for containers {based_on_container}.",
        from_target_image="scratch",
        cmd=["/bin/sh"],
        package_list=[pkg.name for pkg in _get_micro_package_list(os_version)],
        min_release_counter={
            OsVersion.SP7: 41,  # be newer than the newest kiwi based image on SP6
            OsVersion.SL16_0: 6,
        },
        build_stage_custom_end=(
            (
                f"{DOCKERFILE_RUN} rpm --root /target --import /usr/lib/rpm/gnupg/keys/gpg-pubkey-3fa1d6ce-67c856ee.asc"
                if os_version.is_sle15 or os_version.is_sl16
                else ""
            )
            + textwrap.dedent(f"""
            {DOCKERFILE_RUN} zypper -n install jdupes \\
                && jdupes -1 -L -r /target/usr/""")
        ),
        post_build_checks_containers=os_version in CAN_BE_SAC_VERSION,
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


INIT_CONTAINERS = [
    OsContainer(
        name="init",
        os_version=os_version,
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Init",
        custom_description="Systemd environment for containers {based_on_container}. {podman_only}",
        package_list=[
            "systemd",
            (
                "systemd-default-settings-branding-openSUSE"
                if os_version.is_tumbleweed
                else "systemd-default-settings-branding-SLE"
            ),
            "gzip",
            *os_version.release_package_names,
        ],
        min_release_counter={
            OsVersion.SP7: 40,
            OsVersion.SL16_0: 4,
        },
        is_singleton_image=(
            # preserve backwards compatibility on already released distributions
            os_version not in (OsVersion.SP6, OsVersion.TUMBLEWEED)
        ),
        cmd=["/usr/lib/systemd/systemd"],
        extra_labels={
            "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
        },
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        build_stage_custom_end=textwrap.dedent(
            f"""
            {DOCKERFILE_RUN} install -d -m 0755 /etc/systemd/system.conf.d/ \\
                && printf "[Manager]\\nLogColor=no" > \\
                    /etc/systemd/system.conf.d/01-sle-bci-nocolor.conf
            {DOCKERFILE_RUN} {_DISABLE_GETTY_AT_TTY1_SERVICE}
            {DOCKERFILE_RUN} useradd --no-create-home --uid 497 systemd-coredump
            """
        ),
        custom_end=textwrap.dedent(
            """
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


def _get_asset_script(baseurl: str, binaries: list[str]) -> str:
    return "".join(
        f"#!RemoteAssetUrl: {baseurl}{binary}\nCOPY {os.path.basename(binary)} .\n"
        for binary in binaries
    ).strip()


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

    if os_version not in ALL_BASE_OS_VERSIONS:
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
        _get_asset_script(_FIPS_ASSET_BASEURL, bins)
        + (custom_install_bins if bins else "")
        + (custom_set_fips_mode if os_version not in (OsVersion.SP3,) else "")
    )


def _get_fips_custom_env() -> str:
    return textwrap.dedent(
        """
        ENV GNUTLS_FORCE_FIPS_MODE=1
        ENV LIBGCRYPT_FORCE_FIPS_MODE=1
        ENV LIBICA_FIPS_FLAG=1
        ENV NSS_FIPS=1
        ENV OPENSSL_FIPS=1
        ENV OPENSSL_FORCE_FIPS_MODE=1
        """
    )


def _get_fips_pretty_name(os_version: OsVersion) -> str:
    """Return a pretty name for FIPS enforcing containers."""

    if os_version.is_ltss:
        if os_version == OsVersion.SP3:
            return f"{os_version.pretty_os_version_no_dash} FIPS-140-2"
        elif os_version == OsVersion.SP4:
            return f"{os_version.pretty_os_version_no_dash} FIPS-140-3"

    if os_version.is_sle15 or os_version.is_sl16 or os_version.is_tumbleweed:
        return f"{os_version.pretty_os_version_no_dash} FIPS-140-3 mode".strip()

    raise NotImplementedError(f"Unsupported os_version: {os_version}")


def _get_supported_until_fips(os_version: OsVersion) -> datetime.date | None:
    """Returns the end of LTSS for images under LTSS, otherwise end of general support if known"""
    match os_version:
        case OsVersion.SP3:
            return datetime.date(2025, 12, 31)
        case OsVersion.SP4:
            return datetime.date(2026, 12, 31)
        case _:
            return _SUPPORTED_UNTIL_SLE.get(os_version)


def _get_fips_base_kwargs(os_version: OsVersion) -> dict:
    return {
        "name": "base-fips",
        "exclusive_arch": [Arch.X86_64] if os_version.is_ltss else None,
        "os_version": os_version,
        "build_recipe_type": BuildType.DOCKER,
        "support_level": SupportLevel.L3,
        "is_singleton_image": (
            # preserve backwards compatibility on already released distributions
            os_version
            not in (
                OsVersion.SP3,
                OsVersion.SP4,
                OsVersion.SP5,
                OsVersion.SP6,
                OsVersion.TUMBLEWEED,
            )
        ),
        "supported_until": _get_supported_until_fips(os_version),
        "is_latest": (
            os_version in CAN_BE_LATEST_BASE_OS_VERSION
            or os_version in ALL_OS_LTSS_VERSIONS
        ),
        "pretty_name": _get_fips_pretty_name(os_version),
        "package_list": (
            [*os_version.release_package_names, "coreutils"]
            + (
                ["fipscheck"]
                if os_version == OsVersion.SP3
                else ["crypto-policies-scripts"]
            )
            + (["patterns-base-fips"] if os_version.is_sl16 else [])
        ),
        "extra_labels": {
            "usage": "This container should only be used on a FIPS enabled host (fips=1 on kernel cmdline)."
        },
        "custom_end": _get_fips_base_custom_end(os_version) + _get_fips_custom_env(),
        "min_release_counter": {
            OsVersion.SP6: 30,
            OsVersion.SL16_0: 4,
        },
        "post_build_checks_containers": os_version in CAN_BE_SAC_VERSION,
    }


FIPS_BASE_CONTAINERS = [
    OsContainer(
        **_get_fips_base_kwargs(os_version),
    )
    # SP5 is known to be having a non-working libgcrypt for FIPS mode
    for os_version in ALL_OS_VERSIONS - {OsVersion.SP5}
]

FIPS_MICRO_CONTAINERS = [
    OsContainer(
        name="micro-fips",
        os_version=os_version,
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
        is_singleton_image=(
            # preserve backwards compatibility on already released distributions
            not os_version.is_sle15
        ),
        pretty_name=f"Micro {_get_fips_pretty_name(os_version)}",
        custom_description="A micro container in FIPS-140-3 mode for containers {based_on_container}.",
        from_target_image="scratch",
        cmd=["/bin/sh"],
        package_list=[pkg.name for pkg in _get_micro_package_list(os_version)]
        + ["patterns-base-fips", "libopenssl3"],
        build_stage_custom_end=textwrap.dedent(
            f"""
            {DOCKERFILE_RUN} zypper -n install jdupes \\
                && jdupes -1 -L -r /target/usr/"""
        ),
        custom_end=_get_fips_custom_env(),
        min_release_counter={
            OsVersion.SL16_0: 5,
        },
        post_build_checks_containers=os_version in CAN_BE_SAC_VERSION,
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


def _get_minimal_kwargs(os_version: OsVersion):
    package_list = [
        Package(name, pkg_type=PackageType.DELETE)
        for name in ("grep", "diffutils", "info", "fillup", "libzio1")
    ]
    # the last user of libpcre1 on SP6 is grep which we deinstall above
    if os_version in (OsVersion.SP6,):
        package_list.append(Package("libpcre1", pkg_type=PackageType.DELETE))

    package_list.extend(_get_micro_package_list(os_version))
    package_list.append(Package("jdupes", pkg_type=PackageType.BOOTSTRAP))
    if os_version.is_sle15:
        # in SLE15, rpm still depends on Perl.
        package_list.extend(
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in ("rpm-ndb", "perl-base")
        )
    else:
        package_list.append(Package("rpm", pkg_type=PackageType.BOOTSTRAP))
    kwargs = {
        "from_image": None,
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
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
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

            # don't have duplicate licenses of the same type
            jdupes -1 -L -r /usr/share/licenses
            rpm -e jdupes
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
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
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
        """
        ),
        config_sh_interpreter="/bin/sh",
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


KERNEL_MODULE_CONTAINERS = []

for os_version in ALL_OS_VERSIONS - {OsVersion.TUMBLEWEED}:
    if os_version.is_sl16:
        prefix = "sle16"
        pretty_prefix = "SLES 16"
    else:
        assert os_version.is_sle15
        prefix = "sle15"
        pretty_prefix = "SLE 15"

    KERNEL_MODULE_CONTAINERS.append(
        OsContainer(
            name=f"{prefix}-kernel-module-devel",
            pretty_name=f"{pretty_prefix} Kernel module development",
            logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
            os_version=os_version,
            min_release_counter={
                OsVersion.SP7: 40,
                OsVersion.SL16_0: 17,
            },
            supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
            is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
            package_list=(
                [
                    "kernel-devel",
                    "kernel-default-devel",
                    "gcc",
                    "git-core",
                    "kmod",
                    "make",
                    "patch",
                    "gawk",
                    "rpm-build",
                    *os_version.release_package_names,
                ]
                # tar is not in bci-base in 15.4, but we need it to unpack tarballs
                + (["tar"] if os_version == OsVersion.SP4 else [])
                + (["kernel-syms"] if os_version.is_sle15 else [])
                + (["suse-module-tools-scriptlets"] if os_version.is_sl16 else [])
            ),
            build_stage_custom_end=textwrap.dedent(
                f"""
                #!ArchExclusiveLine: aarch64
                {DOCKERFILE_RUN} if [ "$(uname -m)" = "aarch64" ]; then zypper -n install kernel-64kb-devel; fi
                """
                if os_version.is_sl16
                else f"""
                #!ArchExclusiveLine: x86_64 aarch64
                {DOCKERFILE_RUN} zypper -n install mokutil
                """
            ),
            extra_files={"_constraints": generate_disk_size_constraints(8)},
        )
    )


OSC_CHECKOUT = (Path(__file__).parent / "gitea-runner" / "osc_checkout").read_bytes()

GITEA_RUNNER_CONTAINER = OsContainer(
    name="gitea-runner",
    pretty_name="Gitea action runner",
    os_version=OsVersion.TUMBLEWEED,
    is_latest=True,
    package_list=[
        "osc",
        "expect",
        "obs-service-format_spec_file",
        "obs-service-source_validator",
        "typescript",
        "git-core",
        *OsVersion.TUMBLEWEED.release_package_names,
    ],
    extra_files={"osc_checkout": OSC_CHECKOUT},
    custom_end=f"""COPY osc_checkout /usr/bin/osc_checkout
{DOCKERFILE_RUN} chmod +x /usr/bin/osc_checkout""",
)
