"""Base container images maintained by the BCI generator"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_BASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_BASE_OS_VERSION
from bci_build.os_version import CAN_BE_SAC_VERSION
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import OsContainer
from bci_build.package import Package


def _get_nano_package_list(os_version: OsVersion) -> list[Package]:
    return [
        Package(name, pkg_type=PackageType.BOOTSTRAP)
        for name in ("ca-certificates-mozilla-prebuilt", "coreutils", "timezone")
        + os_version.eula_package_names
        + os_version.release_package_names
    ]


NANO_CONTAINERS = [
    OsContainer(
        name="nano",
        os_version=os_version,
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE.get(os_version),
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        is_latest=os_version in CAN_BE_LATEST_BASE_OS_VERSION,
        is_singleton_image=True,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Nano",
        custom_description="A nano environment for containers {based_on_container}.",
        from_target_image="scratch",
        package_list=[pkg.name for pkg in _get_nano_package_list(os_version)],
        extra_files={
            "pause.c": (Path(__file__).parent / "nano" / "pause.c").read_bytes(),
        },
        build_stage_custom_end=(
            (
                f"{DOCKERFILE_RUN} rpm --root /target --import /usr/lib/rpm/gnupg/keys/gpg-pubkey-3fa1d6ce-67c856ee.asc"
                if not os_version.is_tumbleweed
                else ""
            )
            + textwrap.dedent(f"""
            {DOCKERFILE_RUN} rpm --root /target -e --noscripts --nodeps bash glibc{"" if os_version.is_sle15 else " compat-usrmerge-tools"} coreutils terminfo-base \\
                $(rpm --root /target -qa --qf '%{{NAME}}\\n' | grep -E '^lib') \\
                && rm /target/usr/{{sbin,bin}}/* -v

            COPY pause.c ./pause.c
            {DOCKERFILE_RUN} zypper -n install glibc-devel-static gcc binutils \\
                && gcc -static -nostartfiles -fno-stack-protector pause.c -o /target/usr/bin/pause \\
                && strip -s /target/usr/bin/pause

            {DOCKERFILE_RUN} zypper -n install jdupes \\
                && jdupes -1 -L -r /target/usr/
            {DOCKERFILE_RUN} rm -vf /target/var/lib/zypp/AutoInstalled /target/var/cache/ldconfig/aux-cache
                """)
        ),
        post_build_checks_containers=os_version in CAN_BE_SAC_VERSION,
    )
    for os_version in ALL_BASE_OS_VERSIONS
]
