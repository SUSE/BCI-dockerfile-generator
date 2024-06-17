"""Application Containers that are generated with the BCI tooling"""

from itertools import product
from pathlib import Path

from bci_build.package import ALL_BASE_OS_VERSIONS
from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import BuildType
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.package import Package
from bci_build.package import PackageType
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import _build_tag_prefix
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version
from bci_build.package.versions import to_major_minor_version
from bci_build.package.versions import to_major_version


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
        package_name="pcp-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-init:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        support_level=SupportLevel.L3,
        version=(pcp_ver := get_pkg_version("pcp", os_version)),
        version_in_uid=False,
        additional_versions=[
            to_major_minor_version(pcp_ver),
            to_major_version(pcp_ver),
        ],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%pcp_{ver}%%",
                package_name="pcp",
                parse_version=ver,
            )
            for ver in ("major", "minor")
        ],
        license="(LGPL-2.1+ AND GPL-2.0+)",
        package_list=[
            "pcp",
            "hostname",
            "shadow",
            _envsubst_pkg_name(os_version),
            "util-linux-systemd",
        ],
        entrypoint=["/usr/local/bin/container-entrypoint"],
        cmd=["/usr/lib/systemd/systemd"],
        build_recipe_type=BuildType.DOCKER,
        extra_files=_PCP_FILES,
        volumes=["/var/log/pcp/pmlogger"],
        exposes_tcp=[44321, 44322, 44323],
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
        package_name="389-ds-container",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version_in_uid=False,
        name="389-ds",
        support_level=SupportLevel.L3,
        maintainer="william.brown@suse.com",
        pretty_name="389 Directory Server",
        package_list=["389-ds", "timezone", "openssl", "nss_synth"],
        cmd=["/usr/lib/dirsrv/dscontainer", "-r"],
        version="%%389ds_version%%",
        extra_files=_389DS_FILES,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%389ds_version%%",
                package_name="389-ds",
                parse_version="minor",
            )
        ],
        exposes_tcp=[3389, 3636],
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

_POSTGRES_ENTRYPOINT = (
    Path(__file__).parent / "postgres" / "entrypoint.sh"
).read_bytes()
_POSTGRES_LICENSE = (Path(__file__).parent / "postgres" / "LICENSE").read_bytes()

# first list the SLE15 versions, then the TW specific versions
_POSTGRES_MAJOR_VERSIONS = [16, 15, 14] + [13, 12]
POSTGRES_CONTAINERS = [
    ApplicationStackContainer(
        package_name=f"postgres-{ver}-image",
        os_version=os_version,
        is_latest=ver == _POSTGRES_MAJOR_VERSIONS[0],
        name="postgres",
        pretty_name=f"PostgreSQL {ver}",
        support_level=SupportLevel.ACC,
        package_list=[f"postgresql{ver}-server", "findutils"],
        version=ver,
        additional_versions=["%%pg_version%%"],
        entrypoint=["/usr/local/bin/docker-entrypoint.sh"],
        cmd=["postgres"],
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": "%%pg_version%%",
            "PGDATA": "/var/lib/pgsql/data",
        },
        extra_files={
            "docker-entrypoint.sh": _POSTGRES_ENTRYPOINT,
            "LICENSE": _POSTGRES_LICENSE,
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(8),
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%pg_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version="minor",
            )
        ],
        volumes=["$PGDATA"],
        exposes_tcp=[5432],
        custom_end=rf"""COPY docker-entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/docker-entrypoint.sh; \
    sed -i -e 's/exec gosu postgres "/exec setpriv --reuid=postgres --regid=postgres --clear-groups -- "/g' /usr/local/bin/docker-entrypoint.sh; \
    mkdir /docker-entrypoint-initdb.d; \
    install -m 1775 -o postgres -g postgres -d /run/postgresql; \
    install -d -m 0700 -o postgres -g postgres $PGDATA; \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql{ver}/postgresql.conf.sample

STOPSIGNAL SIGINT
HEALTHCHECK --interval=10s --start-period=10s --timeout=5s \
    CMD pg_isready -U ${{POSTGRES_USER:-postgres}} -h localhost -p 5432
""",
    )
    for ver, os_version in (
        [(15, variant) for variant in (OsVersion.SP5, OsVersion.TUMBLEWEED)]
        + [
            (16, variant)
            for variant in (OsVersion.SP5, OsVersion.SP6, OsVersion.TUMBLEWEED)
        ]
    )
    + [(pg_ver, OsVersion.TUMBLEWEED) for pg_ver in (14, 13, 12)]
]

PROMETHEUS_PACKAGE_NAME = "golang-github-prometheus-prometheus"
PROMETHEUS_CONTAINERS = [
    ApplicationStackContainer(
        package_name="prometheus-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="prometheus",
        pretty_name="Prometheus",
        package_list=[PROMETHEUS_PACKAGE_NAME],
        version="%%prometheus_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/prometheus"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%prometheus_version%%",
                package_name=PROMETHEUS_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/prometheus"],
        exposes_tcp=[9090],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

ALERTMANAGER_PACKAGE_NAME = "golang-github-prometheus-alertmanager"
ALERTMANAGER_CONTAINERS = [
    ApplicationStackContainer(
        package_name="alertmanager-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="alertmanager",
        pretty_name="Alertmanager",
        package_list=[ALERTMANAGER_PACKAGE_NAME],
        version="%%alertmanager_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/prometheus-alertmanager"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%alertmanager_version%%",
                package_name=ALERTMANAGER_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/prometheus/alertmanager"],
        exposes_tcp=[9093],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

BLACKBOX_EXPORTER_PACKAGE_NAME = "prometheus-blackbox_exporter"
BLACKBOX_EXPORTER_CONTAINERS = [
    ApplicationStackContainer(
        package_name="blackbox_exporter-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="blackbox_exporter",
        pretty_name="Blackbox Exporter",
        package_list=[BLACKBOX_EXPORTER_PACKAGE_NAME],
        version="%%blackbox_exporter_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/blackbox_exporter"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%blackbox_exporter_version%%",
                package_name=BLACKBOX_EXPORTER_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        exposes_tcp=[9115],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

GRAFANA_FILES = {}
for filename in ("run.sh", "LICENSE"):
    GRAFANA_FILES[filename] = (
        Path(__file__).parent / "grafana" / filename
    ).read_bytes()

GRAFANA_PACKAGE_NAME = "grafana"
GRAFANA_CONTAINERS = [
    ApplicationStackContainer(
        package_name="grafana-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="grafana",
        pretty_name="Grafana",
        license="Apache-2.0",
        package_list=[GRAFANA_PACKAGE_NAME],
        version="%%grafana_version%%",
        version_in_uid=False,
        entrypoint=["/run.sh"],
        extra_files=GRAFANA_FILES,
        env={
            "GF_PATHS_DATA": "/var/lib/grafana",
            "GF_PATHS_HOME": "/usr/share/grafana",
            "GF_PATHS_LOGS": "/var/log/grafana",
            "GF_PATHS_PLUGINS": "/var/lib/grafana/plugins",
            "GF_PATHS_PROVISIONING": "/etc/grafana/provisioning",
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%grafana_version%%",
                package_name=GRAFANA_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/grafana"],
        exposes_tcp=[3000],
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
    nginx_version = to_major_minor_version(get_pkg_version("nginx", os_version))

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
                parse_version="minor",
            )
        ],
        "package_list": ["gawk", "nginx", "findutils", _envsubst_pkg_name(os_version)],
        "entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
        "cmd": ["nginx", "-g", "daemon off;"],
        "build_recipe_type": BuildType.DOCKER,
        "extra_files": _NGINX_FILES,
        "support_level": SupportLevel.L3,
        "exposes_tcp": [80],
        "custom_end": f"""{ version_check_lines }
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
        package_name="rmt-nginx-image",
        pretty_name="NGINX for SUSE RMT",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
] + [
    ApplicationStackContainer(
        name="nginx",
        package_name="nginx-image",
        pretty_name="NGINX",
        custom_description="NGINX open source all-in-one load balancer, content cache and web server {based_on_container}.",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

GIT_CONTAINERS = [
    ApplicationStackContainer(
        name="git",
        os_version=os_version,
        support_level=SupportLevel.L3,
        package_name="git-image",
        pretty_name=f"{os_version.pretty_os_version_no_dash} with Git",
        custom_description="A micro environment with Git {based_on_container}.",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        build_recipe_type=BuildType.KIWI,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%git_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%git_version%%",
                package_name="git-core",
                parse_version="minor",
            )
        ],
        license="GPL-2.0-only",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "git-core",
                "openssh-clients",
            )
            + (() if os_version == OsVersion.TUMBLEWEED else ("skelcd-EULA-bci",))
        ],
        # intentionally empty
        config_sh_script="""
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


REGISTRY_CONTAINERS = [
    ApplicationStackContainer(
        name="registry",
        pretty_name="OCI Container Registry (Distribution)",
        package_name="distribution-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%registry_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%registry_version%%",
                package_name="distribution-registry",
                parse_version="minor",
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
        exposes_tcp=[5000],
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


HELM_CONTAINERS = [
    ApplicationStackContainer(
        name="helm",
        pretty_name="Kubernetes Package Manager",
        package_name="helm-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%helm_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%helm_version%%",
                package_name="helm",
                parse_version="minor",
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "ca-certificates-mozilla",
                "helm",
            )
        ],
        entrypoint=["/usr/bin/helm"],
        cmd=["help"],
        build_recipe_type=BuildType.KIWI,
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


TRIVY_CONTAINERS = [
    ApplicationStackContainer(
        name="trivy",
        pretty_name="Container Vulnerability Scanner",
        package_name="trivy-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%trivy_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%trivy_version%%",
                package_name="trivy",
                parse_version="minor",
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

_TOMCAT_VERSIONS = [9, 10]
assert _TOMCAT_VERSIONS == sorted(_TOMCAT_VERSIONS)

TOMCAT_CONTAINERS = [
    ApplicationStackContainer(
        name="tomcat",
        pretty_name=f"Apache Tomcat {tomcat_major}",
        package_name=f"tomcat-{tomcat_major}-image",
        os_version=os_version,
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and tomcat_major == _TOMCAT_VERSIONS[-1]
        ),
        version=tomcat_major,
        additional_versions=["%%tomcat_version%%", "%%tomcat_minor%%"],
        package_list=[
            tomcat_pkg := (
                "tomcat"
                if tomcat_major == _TOMCAT_VERSIONS[0]
                else f"tomcat{tomcat_major}"
            )
        ]
        + (
            ["java-21-openjdk", "java-21-openjdk-headless"]
            if os_version == OsVersion.SP6
            else []
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%tomcat_version%%", package_name=tomcat_pkg
            ),
            Replacement(
                regex_in_build_description="%%tomcat_minor%%",
                package_name=tomcat_pkg,
                parse_version="minor",
            ),
        ],
        cmd=[
            f"/usr/{'libexec' if os_version in( OsVersion.TUMBLEWEED, OsVersion.BASALT) else 'lib'}/tomcat/server",
            "start",
        ],
        exposes_tcp=[8080],
        env={
            "TOMCAT_MAJOR": tomcat_major,
            "TOMCAT_VERSION": "%%tomcat_version%%",
            "CATALINA_HOME": (_CATALINA_HOME := "/usr/share/tomcat"),
            "CATALINA_BASE": _CATALINA_HOME,
            "PATH": f"{_CATALINA_HOME}/bin:$PATH",
        },
        custom_end=rf"""{DOCKERFILE_RUN} mkdir -p /var/log/tomcat; chown --recursive tomcat:tomcat /var/log/tomcat;
{DOCKERFILE_RUN} \
    sed -i /etc/tomcat/logging.properties \
        -e 's|org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.handlers =.*|org.apache.catalina.core.ContainerBase.[Catalina].[localhost].handlers = java.util.logging.ConsoleHandler|' \
        -e 's|org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.\[/manager\]\.handlers =.*|org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/manager].handlers = java.util.logging.ConsoleHandler|' \
        -e 's|org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.\[/host-manager\]\.handlers =.*|org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/host-manager].handlers = java.util.logging.ConsoleHandler|'

WORKDIR $CATALINA_HOME
""",
        entrypoint_user="tomcat",
        logo_url="https://tomcat.apache.org/res/images/tomcat.png",
    )
    for tomcat_major, os_version in product(_TOMCAT_VERSIONS, ALL_BASE_OS_VERSIONS)
]
