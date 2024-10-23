"""Provide an Apache Tomcat container."""

import datetime

from bci_build.container_attributes import PackageType
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import Replacement
from bci_build.package import _build_tag_prefix
from bci_build.registry import publish_registry

# last version needs to be the newest
_TOMCAT_VERSIONS: list[str] = ["9", "10.1"]
assert _TOMCAT_VERSIONS == sorted(_TOMCAT_VERSIONS, key=float)


def _get_sac_supported_until(
    os_version: OsVersion, tomcat_ver: str, jre_major: int
) -> datetime.date | None:
    """Return the predicted minimum end of support date for this os/tomcat/jre combination. We pick
    the minimum time that either the given tomcat or JRE is known to be supported."""
    if os_version.is_tumbleweed:
        return None

    # Taken from https://www.suse.com/releasenotes/x86_64/SUSE-SLES/15-SP6/index.html#java-version
    jre_end_support_dates: dict[int, datetime.date] = {
        21: datetime.date(2031, 6, 30),
        17: datetime.date(2027, 12, 31),
        11: datetime.date(2026, 12, 31),
    }
    # We do not have a documented policy, for now we do 3 years from initial publishing
    tomcat_end_support_dates: dict[str, datetime.date] = {
        "9": datetime.date(2024 + 3, 2, 1),
        "10.1": datetime.date(2024 + 3, 7, 1),
    }
    # If neither is specified we can not determine a minimum
    if (
        tomcat_end_support_dates.get(tomcat_ver) is None
        and jre_end_support_dates.get(jre_major) is None
    ):
        return None
    return min(
        jre_end_support_dates.get(jre_major, datetime.date.max),
        tomcat_end_support_dates.get(tomcat_ver, datetime.date.max),
    )


TOMCAT_CONTAINERS = [
    ApplicationStackContainer(
        name="apache-tomcat",
        package_name=(
            f"apache-tomcat-{tomcat_ver.partition('.')[0]}-image"
            if os_version.is_tumbleweed
            else f"sac-apache-tomcat-{tomcat_ver.partition('.')[0]}-image"
        ),
        _publish_registry=publish_registry(os_version, app_collection=True),
        pretty_name="Apache Tomcat",
        custom_description=(
            "Apache Tomcat is a free and open-source implementation of the Jakarta Servlet, "
            "Jakarta Expression Language, and WebSocket technologies"
        )
        + (", {based_on_container}." if os_version.is_tumbleweed else "."),
        os_version=os_version,
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and tomcat_ver == _TOMCAT_VERSIONS[-1]
            and jre_version == 22
            and os_version.is_tumbleweed
        ),
        version="%%tomcat_version%%",
        tag_version=tomcat_ver,
        build_flavor=f"openjdk{jre_version}",
        _min_release_counter=None if not os_version.is_sle15 else 55,
        supported_until=_get_sac_supported_until(
            os_version=os_version, tomcat_ver=tomcat_ver, jre_major=jre_version
        ),
        from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        package_list=[
            tomcat_pkg := (
                "tomcat"
                if tomcat_ver == _TOMCAT_VERSIONS[0]
                else f"tomcat{tomcat_ver.partition('.')[0]}"
            ),
            # currently needed by testsuite
            "curl",
            # currently needed by custom_end
            "sed",
            Package("util-linux", PackageType.DELETE),
        ]
        + [f"java-{jre_version}-openjdk", f"java-{jre_version}-openjdk-headless"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%tomcat_version%%", package_name=tomcat_pkg
            ),
        ],
        cmd=[
            f"/usr/{'libexec' if os_version in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0) else 'lib'}/tomcat/server",
            "start",
        ],
        exposes_ports=["8080"],
        env={
            "TOMCAT_MAJOR": int(tomcat_ver.partition(".")[0]),
            "TOMCAT_VERSION": "%%tomcat_version%%",
            "CATALINA_HOME": (_CATALINA_HOME := "/usr/share/tomcat"),
            "CATALINA_BASE": _CATALINA_HOME,
            "PATH": f"{_CATALINA_HOME}/bin:$PATH",
        },
        custom_end=rf"""{DOCKERFILE_RUN} mkdir -p /var/log/tomcat; chown --recursive tomcat:tomcat /var/log/tomcat
{DOCKERFILE_RUN} ln -s {_CATALINA_HOME} /usr/local/tomcat
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
    for tomcat_ver, os_version, jre_version in (
        ("10.1", OsVersion.TUMBLEWEED, 23),
        ("10.1", OsVersion.TUMBLEWEED, 21),
        ("10.1", OsVersion.TUMBLEWEED, 17),
        ("9", OsVersion.TUMBLEWEED, 17),
        ("10.1", OsVersion.SP6, 21),
        ("10.1", OsVersion.SP6, 17),
        # (10.1, OsVersion.SP7, 21),
    )
]

TOMCAT_CRATE = ContainerCrate(TOMCAT_CONTAINERS)
