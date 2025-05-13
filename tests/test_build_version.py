"""Tests for buildversions that match requirements for interoperability between dockerfiles and kiwi build recipes"""

from datetime import date

import pytest

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package import DevelopmentContainer
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import _build_tag_prefix
from bci_build.registry import publish_registry


@pytest.mark.parametrize(
    "build_version_docker,build_version_kiwi,image",
    [
        (
            # codestream.majorversion
            "15.6.27",
            "15.6.27",
            DevelopmentContainer(
                name="test",
                pretty_name="Test",
                supported_until=date(2024, 2, 1),
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.SP6,
                version="27",
            ),
        ),
        (
            # Codestream.majorversion.stabilitytagindex
            "15.7.25.1",
            "15.7.25.1",
            DevelopmentContainer(
                name="test",
                pretty_name="DevelopmentContainer Test",
                package_list=["gcc", "emacs"],
                package_name="test-image",
                stability_tag="stable",
                os_version=OsVersion.SP7,
                version="%%emacs_ver%%",
                tag_version="25",
            ),
        ),
        (
            None,
            f"{date.today().year}.0.28",
            DevelopmentContainer(
                exclusive_arch=[Arch.X86_64, Arch.S390X],
                name="test",
                pretty_name="Test",
                package_list=["emacs"],
                os_version=OsVersion.TUMBLEWEED,
                is_latest=True,
                license="BSD",
                version="28.2",
                tag_version="28",
                additional_names=["emacs"],
            ),
        ),
    ],
)
def test_build_versions_developmentcontainer(
    build_version_docker: str, build_version_kiwi: str, image: DevelopmentContainer
) -> None:
    image.build_recipe_type = BuildType.DOCKER
    assert image.build_version == build_version_docker
    image.build_recipe_type = BuildType.KIWI
    assert image.build_version == build_version_kiwi


@pytest.mark.parametrize(
    "build_version_docker,build_version_kiwi,image",
    [
        (
            None,
            f"{date.today().year}.0.0",
            OsContainer(
                name="test",
                os_version=OsVersion.TUMBLEWEED,
                support_level=SupportLevel.L3,
                package_name="test-image",
                logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
                is_latest=True,
                pretty_name=f"{OsVersion.TUMBLEWEED.pretty_os_version_no_dash} Test",
                custom_description="A test environment for containers.",
                from_image=None,
                build_recipe_type=BuildType.KIWI,
                package_list=[
                    Package(name, pkg_type=PackageType.BOOTSTRAP)
                    for name in (
                        "bash",
                        "ca-certificates-mozilla-prebuilt",
                        # ca-certificates-mozilla-prebuilt requires /bin/cp, which is otherwise not resolved…
                        "coreutils",
                    )
                    + tuple(("skelcd-EULA-test",))
                    + tuple(("Test-release",))
                ],
                # intentionally empty
                config_sh_script="""
""",
            ),
        ),
    ],
)
def test_build_version_oscontainer(
    build_version_docker: str, build_version_kiwi: str, image: OsContainer
) -> None:
    image.build_recipe_type = BuildType.DOCKER
    assert image.build_version == build_version_docker
    image.build_recipe_type = BuildType.KIWI
    assert image.build_version == build_version_kiwi


@pytest.mark.parametrize(
    "build_version_docker,build_version_kiwi,image",
    [
        (
            # codestreamversion.tag_version
            "15.6.42",
            "15.6.42",
            ApplicationStackContainer(
                name="test",
                pretty_name="Test",
                supported_until=date(2024, 2, 1),
                package_list=["emacs", Package("util-linux", PackageType.DELETE)],
                package_name="test-image",
                os_version=(os_version := OsVersion.SP6),
                from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
                version="%%emacs_version%%",
                tag_version=42,
            ),
        ),
        (
            # appcollection always wants the full app version
            "%%emacs_version%%",
            "%%emacs_version%%",
            ApplicationStackContainer(
                name="test",
                pretty_name="Test",
                supported_until=date(2024, 2, 1),
                package_list=["emacs", Package("util-linux", PackageType.DELETE)],
                package_name="test-image",
                os_version=(os_version := OsVersion.SP6),
                _publish_registry=publish_registry(os_version, app_collection=True),
                from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
                version="%%emacs_version%%",
                tag_version=42,
            ),
        ),
    ],
)
def test_build_versions_applicationstackcontainer(
    build_version_docker: str, build_version_kiwi: str, image: ApplicationStackContainer
) -> None:
    image.build_recipe_type = BuildType.DOCKER
    assert image.build_version == build_version_docker
    image.build_recipe_type = BuildType.KIWI
    assert image.build_version == build_version_kiwi
