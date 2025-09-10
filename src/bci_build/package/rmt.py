"""SUSE Repository Mirroring Tool (RMT) container definitions"""

from pathlib import Path

from bci_build.container_attributes import BuildType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_package_version_check

_RMT_ENTRYPOINT = (Path(__file__).parent / "rmt-server" / "entrypoint.sh").read_bytes()

RMT_CONTAINERS = [
    ApplicationStackContainer(
        name="rmt-server",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        pretty_name="SUSE RMT server",
        build_recipe_type=BuildType.DOCKER,
        version="%%rmt_version%%",
        tag_version="2",
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%rmt_version%%",
                package_name="rmt-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        version_in_uid=False,
        support_level=SupportLevel.L3,
        min_release_counter={
            OsVersion.SP7: 70,
        },
        package_list=["rmt-server", "catatonit", "bash"],
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        cmd=["/usr/share/rmt/bin/rails", "server", "-e", "production"],
        env={"RAILS_ENV": "production", "LANG": "en"},
        extra_files={"entrypoint.sh": _RMT_ENTRYPOINT},
        custom_end=f"""{generate_package_version_check("rmt-server", "2", ParseVersion.MAJOR)}
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
{DOCKERFILE_RUN} chmod +x /usr/local/bin/entrypoint.sh
""",
    )
    for os_version in {v for v in ALL_NONBASE_OS_VERSIONS if v != OsVersion.SL16_0}
]
