"""Application Containers that are generated with the BCI tooling"""

from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag

_GRAFANA_FILES = {}
for filename in ("run.sh", "LICENSE"):
    _GRAFANA_FILES[filename] = (
        Path(__file__).parent / "grafana" / filename
    ).read_bytes()

_GRAFANA_PACKAGE_NAME = "grafana"
GRAFANA_CONTAINERS = [
    ApplicationStackContainer(
        name="grafana",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="Grafana",
        license="AGPL-3.0-only",
        package_list=(_GRAFANA_PACKAGE_NAME, "grep", "sed", "curl"),
        version="%%grafana_patch_version%%",
        additional_versions=["%%grafana_minor_version%%", "%%grafana_major_version%%"],
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version_in_uid=False,
        is_singleton_image=True,
        entrypoint=["/run.sh"],
        extra_files=_GRAFANA_FILES,
        env={
            "GF_PATHS_DATA": "/var/lib/grafana",
            "GF_PATHS_HOME": "/usr/share/grafana",
            "GF_PATHS_LOGS": "/var/log/grafana",
            "GF_PATHS_PLUGINS": "/var/lib/grafana/plugins",
            "GF_PATHS_PROVISIONING": "/etc/grafana/provisioning",
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%grafana_{level}_version%%",
                package_name=_GRAFANA_PACKAGE_NAME,
                parse_version=level,
            )
            for level in (ParseVersion.MAJOR, ParseVersion.MINOR, ParseVersion.PATCH)
        ],
        volumes=["/var/lib/grafana"],
        exposes_ports=[TCP(3000)],
        custom_end=f"""COPY run.sh /run.sh
{DOCKERFILE_RUN} chmod +x /run.sh
        """,
    )
    for os_version in {v for v in ALL_NONBASE_OS_VERSIONS if v != OsVersion.SLE16_0}
]
