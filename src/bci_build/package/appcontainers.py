"""Application Containers that are generated with the BCI tooling"""

from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import CAN_BE_LATEST_SLFO_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import _build_tag_prefix
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion


def _envsubst_pkg_name(os_version: OsVersion) -> str:
    return "envsubst" if os_version == OsVersion.TUMBLEWEED else "gettext-runtime"


_PCP_FILES = {}
for filename in (
    "container-entrypoint",
    "pmproxy.conf.template",
    "10-host_mount.conf.template",
    "pmcd",
    "pmlogger",
    "healthcheck",
):
    _PCP_FILES[filename] = (Path(__file__).parent / "pcp" / filename).read_bytes()

PCP_CONTAINERS = [
    ApplicationStackContainer(
        name="pcp",
        pretty_name="Performance Co-Pilot (pcp)",
        custom_description="{pretty_name} container {based_on_container}. {podman_only}",
        from_image=f"{_build_tag_prefix(os_version)}/bci-init:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_SLFO_OS_VERSION,
        support_level=SupportLevel.L3,
        version=(pcp_ver := get_pkg_version("pcp", os_version)),
        version_in_uid=False,
        is_singleton_image=True,
        additional_versions=[
            format_version(pcp_ver, ParseVersion.MINOR),
            format_version(pcp_ver, ParseVersion.MAJOR),
        ],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%pcp_{ver}%%",
                package_name="pcp",
                parse_version=ver,
            )
            for ver in (ParseVersion.MAJOR, ParseVersion.MINOR)
        ],
        license="(LGPL-2.1+ AND GPL-2.0+)",
        package_list=[
            "pcp",
            "hostname",
            "procps",
            "shadow",
            _envsubst_pkg_name(os_version),
            "util-linux-systemd",
        ],
        entrypoint=["/usr/local/bin/container-entrypoint"],
        cmd=["/usr/lib/systemd/systemd"],
        build_recipe_type=BuildType.DOCKER,
        extra_files=_PCP_FILES,
        volumes=["/var/log/pcp/pmlogger"],
        exposes_ports=[TCP(44321), TCP(44322), TCP(44323)],
        custom_end=f"""
{DOCKERFILE_RUN} mkdir -p /usr/share/container-scripts/pcp; mkdir -p /etc/sysconfig
COPY container-entrypoint healthcheck /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/container-entrypoint /usr/local/bin/healthcheck
COPY pmproxy.conf.template 10-host_mount.conf.template /usr/share/container-scripts/pcp/
COPY pmcd pmlogger /etc/sysconfig/

# Create all the users
{DOCKERFILE_RUN} systemd-sysusers

HEALTHCHECK --start-period=30s --timeout=20s --interval=10s --retries=3 \
    CMD /usr/local/bin/healthcheck
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


def _generate_prometheus_family_healthcheck(port: int) -> str:
    return rf"""HEALTHCHECK --interval=5s --timeout=5s --retries=5 \
    CMD ["/usr/bin/curl", "-m", "2", "-sf", "http://localhost:{port}/-/healthy"]
"""


_PROMETHEUS_PACKAGE_NAME = "golang-github-prometheus-prometheus"
_PROMETHEUS_PORT = 9090
PROMETHEUS_CONTAINERS = [
    ApplicationStackContainer(
        name="prometheus",
        pretty_name="Prometheus",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        package_list=[_PROMETHEUS_PACKAGE_NAME, "curl"],
        version="%%prometheus_patch_version%%",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        additional_versions=[
            "%%prometheus_minor_version%%",
            "%%prometheus_major_version%%",
        ],
        version_in_uid=False,
        entrypoint=["/usr/bin/prometheus"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%prometheus_{level}_version%%",
                package_name=_PROMETHEUS_PACKAGE_NAME,
                parse_version=level,
            )
            for level in (ParseVersion.MAJOR, ParseVersion.MINOR, ParseVersion.PATCH)
        ],
        volumes=["/var/lib/prometheus"],
        exposes_ports=[TCP(_PROMETHEUS_PORT)],
        custom_end=_generate_prometheus_family_healthcheck(_PROMETHEUS_PORT),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

_ALERTMANAGER_PACKAGE_NAME = "golang-github-prometheus-alertmanager"
_ALERTMANAGER_PORT = 9093
ALERTMANAGER_CONTAINERS = [
    ApplicationStackContainer(
        name="alertmanager",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="Alertmanager",
        package_list=[_ALERTMANAGER_PACKAGE_NAME, "curl"],
        version="%%alertmanager_patch_version%%",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        additional_versions=["%%alertmanager_minor_version%%"],
        version_in_uid=False,
        is_singleton_image=True,
        entrypoint=["/usr/bin/prometheus-alertmanager"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%alertmanager_{level}_version%%",
                package_name=_ALERTMANAGER_PACKAGE_NAME,
                parse_version=level,
            )
            for level in (ParseVersion.MINOR, ParseVersion.PATCH)
        ],
        volumes=["/var/lib/prometheus/alertmanager"],
        exposes_ports=[TCP(_ALERTMANAGER_PORT)],
        custom_end=_generate_prometheus_family_healthcheck(_ALERTMANAGER_PORT),
    )
    for os_version in (OsVersion.SP7, OsVersion.TUMBLEWEED)
]

_BLACKBOX_EXPORTER_PACKAGE_NAME = "prometheus-blackbox_exporter"
_BLACKBOX_PORT = 9115
BLACKBOX_EXPORTER_CONTAINERS = [
    ApplicationStackContainer(
        name="blackbox_exporter",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="Blackbox Exporter",
        package_list=[_BLACKBOX_EXPORTER_PACKAGE_NAME, "curl"],
        version="%%blackbox_exporter_patch_version%%",
        additional_versions=["%%blackbox_exporter_minor_version%%"],
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version_in_uid=False,
        is_singleton_image=True,
        entrypoint=["/usr/bin/blackbox_exporter"],
        cmd=["--config.file=/etc/prometheus/blackbox.yml"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%blackbox_exporter_{level}_version%%",
                package_name=_BLACKBOX_EXPORTER_PACKAGE_NAME,
                parse_version=level,
            )
            for level in (ParseVersion.MINOR, ParseVersion.PATCH)
        ],
        exposes_ports=[TCP(_BLACKBOX_PORT)],
        custom_end=_generate_prometheus_family_healthcheck(_BLACKBOX_PORT),
    )
    for os_version in (OsVersion.SP7, OsVersion.TUMBLEWEED)
]
