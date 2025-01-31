"""Application Containers that are generated with the BCI tooling"""

from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import _build_tag_prefix
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version


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
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        support_level=SupportLevel.L3,
        version=(pcp_ver := get_pkg_version("pcp", os_version)),
        version_in_uid=False,
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

# This can be removed after the pcp dependency on sysconfig is removed
{DOCKERFILE_RUN} systemctl disable wicked wickedd || :

HEALTHCHECK --start-period=30s --timeout=20s --interval=10s --retries=3 \
    CMD /usr/local/bin/healthcheck
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


_389DS_FILES: dict[str, str | bytes] = {}
_fname = "nsswitch.conf"
_389DS_FILES[_fname] = (Path(__file__).parent / "389-ds" / _fname).read_bytes()

THREE_EIGHT_NINE_DS_CONTAINERS = [
    ApplicationStackContainer(
        name="389-ds",
        package_name="389-ds-container",
        exclusive_arch=[Arch.AARCH64, Arch.PPC64LE, Arch.S390X, Arch.X86_64],
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version_in_uid=False,
        support_level=SupportLevel.L3,
        oci_authors="william.brown@suse.com",
        pretty_name="389 Directory Server",
        package_list=["389-ds", "timezone", "openssl", "nss_synth"],
        cmd=["/usr/lib/dirsrv/dscontainer", "-r"],
        version="%%389ds_version%%",
        extra_files=_389DS_FILES,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%389ds_version%%",
                package_name="389-ds",
                parse_version=ParseVersion.MINOR,
            )
        ],
        exposes_ports=[TCP(3389), TCP(3636)],
        volumes=["/data"],
        custom_end=rf"""
COPY nsswitch.conf /etc/nsswitch.conf

{DOCKERFILE_RUN} mkdir -p /data/config; \
    mkdir -p /data/ssca; \
    mkdir -p /data/run; \
    mkdir -p /var/run/dirsrv; \
    ln -s /data/config /etc/dirsrv/slapd-localhost; \
    ln -s /data/ssca /etc/dirsrv/ssca; \
    ln -s /data/run /var/run/dirsrv

HEALTHCHECK --start-period=5m --timeout=5s --interval=5s --retries=2 \
    CMD /usr/lib/dirsrv/dscontainer -H
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
        additional_versions=["%%alertmanager_minor_version%%"],
        version_in_uid=False,
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
    for os_version in ALL_NONBASE_OS_VERSIONS
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
        version_in_uid=False,
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
    for os_version in ALL_NONBASE_OS_VERSIONS
]

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
        package_list=[_GRAFANA_PACKAGE_NAME],
        version="%%grafana_patch_version%%",
        additional_versions=["%%grafana_minor_version%%", "%%grafana_major_version%%"],
        version_in_uid=False,
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
    for os_version in ALL_NONBASE_OS_VERSIONS
]

_NGINX_FILES = {}
for filename in (
    "docker-entrypoint.sh",
    "LICENSE",
    "20-envsubst-on-templates.sh",
    "30-tune-worker-processes.sh",
    "index.html",
):
    _NGINX_FILES[filename] = (Path(__file__).parent / "nginx" / filename).read_bytes()


def _get_nginx_kwargs(os_version: OsVersion):
    nginx_version = get_pkg_version("nginx", os_version)

    version_check_lines = generate_package_version_check("nginx", nginx_version)

    kwargs = {
        "os_version": os_version,
        "is_latest": os_version in CAN_BE_LATEST_OS_VERSION,
        "version": nginx_version,
        "version_in_uid": False,
        "replacements_via_service": [
            Replacement(
                regex_in_build_description="%%nginx_version%%",
                package_name="nginx",
                parse_version=ParseVersion.MINOR,
            )
        ],
        "package_list": ["gawk", "nginx", "findutils", _envsubst_pkg_name(os_version)],
        "entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
        "cmd": ["nginx", "-g", "daemon off;"],
        "build_recipe_type": BuildType.DOCKER,
        "extra_files": _NGINX_FILES,
        "support_level": SupportLevel.L3,
        "exposes_ports": [TCP(80)],
        "custom_end": f"""{version_check_lines}
{DOCKERFILE_RUN} mkdir /docker-entrypoint.d
COPY [1-3]0-*.sh /docker-entrypoint.d/
COPY docker-entrypoint.sh /usr/local/bin
COPY index.html /srv/www/htdocs/
{DOCKERFILE_RUN} chmod +x /docker-entrypoint.d/*.sh /usr/local/bin/docker-entrypoint.sh
{DOCKERFILE_RUN} install -d -o nginx -g nginx -m 750 /var/log/nginx; \
    ln -sf /dev/stdout /var/log/nginx/access.log; \
    ln -sf /dev/stderr /var/log/nginx/error.log

STOPSIGNAL SIGQUIT
""",
    }

    return kwargs


NGINX_CONTAINERS = [
    ApplicationStackContainer(
        name="rmt-nginx",
        pretty_name="NGINX for SUSE RMT",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in (OsVersion.SP6,)
] + [
    ApplicationStackContainer(
        name="nginx",
        pretty_name="NGINX",
        custom_description="NGINX open source all-in-one load balancer, content cache and web server {based_on_container}.",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


REGISTRY_CONTAINERS = [
    ApplicationStackContainer(
        name="registry",
        package_name="distribution-image",
        pretty_name="OCI Container Registry (Distribution)",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%registry_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%registry_version%%",
                package_name="distribution-registry",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "apache2-utils",
                "ca-certificates-mozilla",
                "distribution-registry",
                "perl",
                "util-linux",
            )
        ],
        entrypoint=["/usr/bin/registry"],
        entrypoint_user="registry",
        cmd=["serve", "/etc/registry/config.yml"],
        build_recipe_type=BuildType.KIWI,
        volumes=["/var/lib/docker-registry"],
        exposes_ports=[TCP(5000)],
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


TRIVY_CONTAINERS = [
    ApplicationStackContainer(
        name="trivy",
        pretty_name="Container Vulnerability Scanner",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%trivy_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%trivy_version%%",
                package_name="trivy",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "ca-certificates-mozilla",
                "trivy",
            )
        ],
        entrypoint=["/usr/bin/trivy"],
        cmd=["help"],
        build_recipe_type=BuildType.KIWI,
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
