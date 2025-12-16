"""Provide an Apache Tomcat container."""

from bci_build.container_attributes import TCP
from bci_build.container_attributes import PackageType
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import _build_tag_prefix
from bci_build.replacement import Replacement

# last version needs to be the newest
_TOMCAT_VERSIONS: list[str] = ["9", "10.1"]
assert _TOMCAT_VERSIONS == sorted(_TOMCAT_VERSIONS, key=float)


def _get_java_packages(jre_major: int) -> list[str]:
    """Determine the right java packages to install, even when using the marketing version"""
    if jre_major == 8:
        return ["java-1_8_0-openjdk", "java-1_8_0-openjdk-headless"]
    return [f"java-{jre_major}-openjdk", f"java-{jre_major}-openjdk-headless"]


TOMCAT_CONTAINERS = [
    ApplicationStackContainer(
        name="apache-tomcat",
        package_name=f"apache-tomcat-{tomcat_ver.partition('.')[0]}-image",
        pretty_name="Apache Tomcat",
        os_version=os_version,
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and tomcat_ver == _TOMCAT_VERSIONS[-1]
            and jre_version == 25
            and os_version.is_tumbleweed
        ),
        build_flavor=f"openjdk{jre_version}",
        version="%%tomcat_version%%",
        tag_version=tomcat_ver,
        from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        package_list=[
            tomcat_pkg := (
                "tomcat"
                if tomcat_ver == _TOMCAT_VERSIONS[0]
                else f"tomcat{tomcat_ver.partition('.')[0]}"
            ),
            Package("util-linux", PackageType.DELETE),
        ]
        + _get_java_packages(jre_version),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%tomcat_version%%", package_name=tomcat_pkg
            ),
        ],
        cmd=[f"{os_version.libexecdir}tomcat/server", "start"],
        exposes_ports=[TCP(8080)],
        env={
            "TOMCAT_MAJOR": int(tomcat_ver.partition(".")[0]),
            "TOMCAT_VERSION": "%%tomcat_version%%",
            "CATALINA_HOME": (_CATALINA_HOME := "/usr/share/tomcat"),
            "CATALINA_BASE": _CATALINA_HOME,
            "PATH": f"{_CATALINA_HOME}/bin:$PATH",
        },
        custom_end=rf"""{DOCKERFILE_RUN} mkdir -p /var/log/tomcat; chown --recursive tomcat:tomcat /var/log/tomcat
{DOCKERFILE_RUN} ln -s {_CATALINA_HOME} /usr/local/tomcat
{DOCKERFILE_RUN} """
        + r"""while IFS= read -r line; do \
  line=${line/org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.handlers =*/org.apache.catalina.core.ContainerBase.[Catalina].[localhost].handlers = java.util.logging.ConsoleHandler}; \
  line=${line/org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.\[\/manager\]\.handlers =*/org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/manager].handlers = java.util.logging.ConsoleHandler}; \
  line=${line/org\.apache\.catalina\.core\.ContainerBase\.\[Catalina\]\.\[localhost\]\.\[\/host-manager\]\.handlers =*/org.apache.catalina.core.ContainerBase.[Catalina].[localhost].[/host-manager].handlers = java.util.logging.ConsoleHandler}; \
  echo "$line" >> /tmp/logging.properties; \
done < /usr/share/tomcat/conf/logging.properties; \

mv /tmp/logging.properties /usr/share/tomcat/conf/logging.properties

WORKDIR $CATALINA_HOME
""",
        entrypoint_user="tomcat",
        logo_url="https://tomcat.apache.org/res/images/tomcat.png",
    )
    for tomcat_ver, os_version, jre_version in (
        ("11", OsVersion.TUMBLEWEED, 25),
        ("11", OsVersion.TUMBLEWEED, 21),
        ("10.1", OsVersion.TUMBLEWEED, 25),
        ("10.1", OsVersion.TUMBLEWEED, 21),
        ("10.1", OsVersion.TUMBLEWEED, 17),
        ("9", OsVersion.TUMBLEWEED, 21),
        ("9", OsVersion.TUMBLEWEED, 17),
    )
]

TOMCAT_CRATE = ContainerCrate(TOMCAT_CONTAINERS)
