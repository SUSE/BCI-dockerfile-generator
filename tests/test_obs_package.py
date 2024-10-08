from bci_build.container_attributes import BuildType
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package.obs_package import MultiBuildObsPackage

_BASE_KWARGS = {
    "name": "test",
    "package_name": "test-image",
    "pretty_name": "Test",
    "os_version": OsVersion.SP3,
    "package_list": ["sh"],
    "version": "1.0",
}


def test_multibuild_with_multi_flavor_docker():
    pkg = MultiBuildObsPackage(
        package_name="test",
        bcis=[
            DevelopmentContainer(
                **_BASE_KWARGS,
                build_recipe_type=BuildType.DOCKER,
                build_flavor=flavor,
            )
            for flavor in ("flavor1", "flavor2")
        ],
        os_version=_BASE_KWARGS["os_version"],
    )
    assert (
        pkg.multibuild
        == """<multibuild>
    <package>flavor1</package>
    <package>flavor2</package>
</multibuild>"""
    )
