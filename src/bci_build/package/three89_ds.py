"""389 Directory Server built using BCI tooling"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import SET_BLKID_SCAN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_389DS_FILES: dict[str, str | bytes] = {}
_fname = "nsswitch.conf"
_389DS_FILES[_fname] = (Path(__file__).parent / "389-ds" / _fname).read_bytes()

THREE_EIGHT_NINE_DS_CONTAINERS = [
    ApplicationStackContainer(
        name="389-ds",
        package_name=("389-ds-container" if os_version.is_sle15 else None),
        exclusive_arch=[Arch.AARCH64, Arch.PPC64LE, Arch.S390X, Arch.X86_64],
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version_in_uid=False,
        support_level=SupportLevel.L3,
        min_release_counter={OsVersion.TUMBLEWEED: 35},
        oci_authors="william.brown@suse.com",
        pretty_name="389 Directory Server",
        package_list=(
            ["389-ds", "timezone", "openssl", "nss_synth"]
            + (["aaa_base"] if os_version.is_sle15 else [])
        ),
        cmd=["/usr/lib/dirsrv/dscontainer", "-r"],
        version="%%389ds_version%%",
        tag_version=format_version(
            three_eight_nine := get_pkg_version("389-ds", os_version),
            ParseVersion.MINOR,
        ),
        extra_files=_389DS_FILES,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%389ds_version%%",
                package_name="389-ds",
                parse_version=ParseVersion.PATCH,
            )
        ],
        exposes_ports=[TCP(3389), TCP(3636)],
        volumes=["/data"],
        build_stage_custom_end=generate_package_version_check(
            "389-ds", three_eight_nine, use_target=True
        ),
        custom_end=(
            (SET_BLKID_SCAN if os_version.is_sle15 else "")
            + textwrap.dedent(rf"""
                COPY nsswitch.conf /etc/nsswitch.conf

                {DOCKERFILE_RUN} install -d -o dirsrv -g dirsrv /data; \
                    install -d -o dirsrv -g dirsrv /data/config  /data/ssca /data/run /var/run/dirsrv; \
                    ln -s /data/config /etc/dirsrv/slapd-localhost; \
                    ln -s /data/ssca /etc/dirsrv/ssca; \
                    ln -s /data/run /var/run/dirsrv; \
                    chown -R dirsrv: /data /var/run/dirsrv;\
                    chgrp -R dirsrv /etc/dirsrv;

                HEALTHCHECK --start-period=5m --timeout=5s --interval=5s --retries=2 \
                    CMD /usr/lib/dirsrv/dscontainer -H
                """)
        ),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
