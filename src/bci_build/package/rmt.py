"""SUSE Repository Mirroring Tool (RMT) container definitions"""

from pathlib import Path

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import BuildType
from bci_build.package import ParseVersion
from bci_build.package import Replacement

_RMT_ENTRYPOINT = (Path(__file__).parent / "rmt-server" / "entrypoint.sh").read_bytes()

RMT_CONTAINERS = [
    ApplicationStackContainer(
        name="rmt-server",
        package_name="rmt-server-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        pretty_name="SUSE RMT Server",
        build_recipe_type=BuildType.DOCKER,
        version="%%rmt_version%%",
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%rmt_version%%",
                package_name="rmt-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        version_in_uid=False,
        package_list=["rmt-server", "catatonit"],
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        cmd=["/usr/share/rmt/bin/rails", "server", "-e", "production"],
        env={"RAILS_ENV": "production", "LANG": "en"},
        extra_files={"entrypoint.sh": _RMT_ENTRYPOINT},
        custom_end=f"""COPY entrypoint.sh /usr/local/bin/entrypoint.sh
{DOCKERFILE_RUN} chmod +x /usr/local/bin/entrypoint.sh
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
