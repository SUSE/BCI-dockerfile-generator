"""Provide an Apache Tomcat container."""

import datetime

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement

from .appcollection import ApplicationCollectionContainer

_TOMCAT_VERSIONS: list[int] = [9, 10]
assert _TOMCAT_VERSIONS == sorted(_TOMCAT_VERSIONS)


def _get_sac_supported_until(
    os_version: OsVersion, tomcat_major: int, jre_major: int
) -> datetime.date:
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
    tomcat_end_support_dates: dict[int, datetime.date] = {
        9: datetime.date(2024 + 3, 2, 1),
        10: datetime.date(2024 + 3, 7, 1),
    }
    # If neither is specified we can not determine a minimum
    if (
        tomcat_end_support_dates.get(tomcat_major) is None
        and jre_end_support_dates.get(jre_major) is None
    ):
        return None
    return min(
        jre_end_support_dates.get(jre_major, datetime.date.max),
        tomcat_end_support_dates.get(tomcat_major, datetime.date.max),
    )


TOMCAT_CONTAINERS = [
    ApplicationCollectionContainer(
        name="apache-tomcat",
        package_name=f"apache-tomcat-{tomcat_major}-java-{jre_version}-image"
        if os_version.is_tumbleweed
        else f"sac-apache-tomcat-{tomcat_major}-java{jre_version}-image",
        pretty_name="Apache Tomcat",
        custom_description=(
            "Apache Tomcat is a free and open-source implementation of the Jakarta Servlet, "
            "Jakarta Expression Language, and WebSocket technologies, {based_on_container}."
        ),
        os_version=os_version,
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and tomcat_major == _TOMCAT_VERSIONS[-1]
            and jre_version == 22
            and os_version.is_tumbleweed
        ),
        version="%%tomcat_version%%",
        tag_version=f"{tomcat_major}-jre{jre_version}",
        supported_until=_get_sac_supported_until(
            os_version=os_version, tomcat_major=tomcat_major, jre_major=jre_version
        ),
        additional_versions=[
            f"%%tomcat_version%%-jre{jre_version}",
            f"%%tomcat_minor%%-jre{jre_version}",
        ],
        package_list=[
            tomcat_pkg := (
                "tomcat"
                if tomcat_major == _TOMCAT_VERSIONS[0]
                else f"tomcat{tomcat_major}"
            )
        ]
        + [f"java-{jre_version}-openjdk", f"java-{jre_version}-openjdk-headless"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%tomcat_version%%", package_name=tomcat_pkg
            ),
            Replacement(
                regex_in_build_description="%%tomcat_minor%%",
                package_name=tomcat_pkg,
                parse_version=ParseVersion.MINOR,
            ),
        ],
        cmd=[
            f"/usr/{'libexec' if os_version in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0) else 'lib'}/tomcat/server",
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
    for tomcat_major, os_version, jre_version in (
        (10, OsVersion.TUMBLEWEED, 22),
        (10, OsVersion.TUMBLEWEED, 21),
        (10, OsVersion.TUMBLEWEED, 17),
        (9, OsVersion.TUMBLEWEED, 17),
        (10, OsVersion.SP6, 21),
    )
]
