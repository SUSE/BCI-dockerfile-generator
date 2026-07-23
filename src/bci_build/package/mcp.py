"""MCP container"""

from bci_build.container_attributes import TCP
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_development_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_MCP_TAG_VERSION = "0"


BUGZILLA_MCP_CONTAINERS = [
    ApplicationStackContainer(
        name="bugzilla-mcp",
        pretty_name="MCP Host for Bugzilla",
        from_image=generate_from_development_tag(os_version, "python", "3.13-base"),
        from_target_image=generate_from_development_tag(
            os_version, "python", "3.13-micro"
        ),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%bugzilla_mcp_version%%",
        tag_version=_MCP_TAG_VERSION,
        version_in_uid=False,
        exposes_ports=[TCP(8000)],
        build_stage_custom_end=generate_package_version_check(
            "bugzilla-mcp",
            _MCP_TAG_VERSION,
            parse_version=ParseVersion.MAJOR,
            use_target=True,
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%bugzilla_mcp_version%%",
                package_name="bugzilla-mcp",
                parse_version=ParseVersion.PATCH,
            )
        ],
        license="Apache-2.0",
        package_list=[
            "bugzilla-mcp",
        ],
        entrypoint=["/usr/bin/mcp-bugzilla"],
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
