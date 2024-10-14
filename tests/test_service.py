import pytest

from bci_build.container_attributes import BuildType
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.service import Service
from bci_build.templates import SERVICE_TEMPLATE


def test_service_without_params_as_xml():
    assert """<service name="foo" mode="buildtime" />""" == str(Service(name="foo"))


def test_service_with_params_as_xml():
    assert (
        """<service name="foo" mode="buildtime"><param name="baz">bar</param><param name="baz">foo</param></service>"""
        == str(Service(name="foo", param=[("baz", "bar"), ("baz", "foo")]))
    )


@pytest.mark.parametrize(
    "replacement, default_file_name, service",
    [
        # bare bone example
        (
            Replacement(regex := "%%ver%%", pkg := "pkgFoo"),
            "Dockerfile",
            Service(
                name=(name := "replace_using_package_version"),
                param=[("file", "Dockerfile"), ("regex", regex), ("package", pkg)],
            ),
        ),
        # the default file name is ignored if the parameter file_name is given
        (
            Replacement(regex, pkg, file_name=(fname := "testfile")),
            "Dockerfile",
            Service(
                name=name,
                param=[("file", fname), ("regex", regex), ("package", pkg)],
            ),
        ),
        # specify a parse_version
        (
            Replacement(regex, pkg, parse_version=ParseVersion.MAJOR),
            "Dockerfile",
            Service(
                name=name,
                param=[
                    ("file", "Dockerfile"),
                    ("regex", regex),
                    ("package", pkg),
                    ("parse-version", "major"),
                ],
            ),
        ),
    ],
)
def test_replacement_to_service(
    replacement: Replacement, default_file_name: str, service: Service
):
    assert replacement.to_service(default_file_name) == service


_BASE_KWARGS = {
    "name": "test",
    "package_name": "test-image",
    "pretty_name": "Test",
    "os_version": OsVersion.SP3,
    "package_list": ["sh"],
    "version": "1.0",
}


def test_service_without_replacement_kiwi():
    assert (
        SERVICE_TEMPLATE.render(
            image=DevelopmentContainer(**_BASE_KWARGS, build_recipe_type=BuildType.KIWI)
        )
        == """<services>
  <service mode="buildtime" name="kiwi_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
</services>"""
    )


def test_service_with_replacement_kiwi():
    assert (
        SERVICE_TEMPLATE.render(
            image=DevelopmentContainer(
                **_BASE_KWARGS,
                build_recipe_type=BuildType.KIWI,
                replacements_via_service=[
                    Replacement(
                        regex_in_build_description="%%re%%", package_name="coreutils"
                    ),
                    Replacement(
                        regex_in_build_description="%%re%%",
                        package_name="coreutils",
                        file_name="replacementfile",
                    ),
                ],
            )
        )
        == """<services>
  <service mode="buildtime" name="kiwi_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">test-image.kiwi</param>
    <param name="regex">%%re%%</param>
    <param name="package">coreutils</param>
  </service>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">replacementfile</param>
    <param name="regex">%%re%%</param>
    <param name="package">coreutils</param>
  </service>
</services>"""
    )


def test_service_with_replacement_docker():
    assert (
        SERVICE_TEMPLATE.render(
            image=DevelopmentContainer(
                **_BASE_KWARGS,
                build_recipe_type=BuildType.DOCKER,
                replacements_via_service=[
                    Replacement(
                        regex_in_build_description="%%my_ver%%", package_name="sh"
                    ),
                    Replacement(
                        regex_in_build_description="%%minor_ver%%",
                        package_name="filesystem",
                        parse_version=ParseVersion.MINOR,
                    ),
                    Replacement(
                        regex_in_build_description="%%minor_ver%%",
                        file_name="replacementfile",
                        package_name="filesystem",
                        parse_version=ParseVersion.MINOR,
                    ),
                ],
            )
        )
        == """<services>
  <service mode="buildtime" name="docker_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">Dockerfile</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">Dockerfile</param>
    <param name="regex">%%minor_ver%%</param>
    <param name="package">filesystem</param>
    <param name="parse-version">minor</param>
  </service>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">replacementfile</param>
    <param name="regex">%%minor_ver%%</param>
    <param name="package">filesystem</param>
    <param name="parse-version">minor</param>
  </service>
</services>"""
    )


def test_service_with_multi_flavor_docker():
    containers = [
        DevelopmentContainer(
            **_BASE_KWARGS,
            build_recipe_type=BuildType.DOCKER,
            build_flavor=flavor,
            replacements_via_service=[
                Replacement(regex_in_build_description="%%my_ver%%", package_name="sh"),
            ],
        )
        for flavor in ("flavor1", "flavor2")
    ]
    ContainerCrate(containers)

    assert (
        SERVICE_TEMPLATE.render(
            image=containers[0],
        )
        == """<services>
  <service mode="buildtime" name="docker_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">Dockerfile.flavor1</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">Dockerfile.flavor2</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
</services>"""
    )
