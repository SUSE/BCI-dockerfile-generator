import pytest

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import ReleaseStage
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.replacement import Replacement
from bci_build.service import Service
from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import SERVICE_TEMPLATE
from bci_build.util import ParseVersion


def test_service_without_params_as_xml():
    assert """<service mode="buildtime" name="foo" />""" == str(Service(name="foo"))


def test_service_with_params_as_xml():
    assert (
        """<service mode="buildtime" name="foo"><param name="baz">bar</param><param name="baz">foo</param></service>"""
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
    "os_version": OsVersion.SP7,
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
  <service mode="buildtime" name="replace_using_package_version">
    <param name="file">test-image.kiwi</param>
    <param name="regex">%%re%%</param>
    <param name="package">coreutils</param>
  </service>
  <service mode="buildtime" name="replace_using_package_version">
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
  <service mode="buildtime" name="replace_using_package_version">
    <param name="file">Dockerfile</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
  <service mode="buildtime" name="replace_using_package_version">
    <param name="file">Dockerfile</param>
    <param name="regex">%%minor_ver%%</param>
    <param name="package">filesystem</param>
    <param name="parse-version">minor</param>
  </service>
  <service mode="buildtime" name="replace_using_package_version">
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
  <service mode="buildtime" name="replace_using_package_version">
    <param name="file">Dockerfile.flavor1</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
  <service mode="buildtime" name="replace_using_package_version">
    <param name="file">Dockerfile.flavor2</param>
    <param name="regex">%%my_ver%%</param>
    <param name="package">sh</param>
  </service>
</services>"""
    )


def test_support_level_overrides_docker():
    image = DevelopmentContainer(
        **_BASE_KWARGS,
        build_recipe_type=BuildType.DOCKER,
        exclusive_arch=[Arch.AARCH64, Arch.X86_64],
        support_level=SupportLevel.L3,
        support_level_overrides={Arch.AARCH64: SupportLevel.TECHPREVIEW},
    )
    assert (
        SERVICE_TEMPLATE.render(image=image)
        == """<services>
  <service mode="buildtime" name="docker_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
</services>"""
    )
    assert """ARG SUPPORT_LEVEL_ARCH_%ARCH%=1
LABEL com.suse.supportlevel="${SUPPORT_LEVEL_ARCH_aarch64:+techpreview}${SUPPORT_LEVEL_ARCH_x86_64:+l3}"
""" in DOCKERFILE_TEMPLATE.render(DOCKERFILE_RUN="RUN", image=image)


def test_support_level_overrides_beta():
    image = DevelopmentContainer(
        **(_BASE_KWARGS | {"os_version": OsVersion.SL16_2}),
        support_level=SupportLevel.L3,
        support_level_overrides={
            Arch.AARCH64: SupportLevel.L3,
            Arch.S390X: SupportLevel.UNSUPPORTED,
        },
    )
    assert image.release_stage == ReleaseStage.BETA
    assert image.support_level_overrides == {
        Arch.AARCH64: SupportLevel.TECHPREVIEW,
        Arch.S390X: SupportLevel.UNSUPPORTED,
    }


def test_support_level_overrides_tumbleweed():
    image = DevelopmentContainer(
        **(_BASE_KWARGS | {"os_version": OsVersion.TUMBLEWEED}),
        support_level_overrides={Arch.AARCH64: SupportLevel.TECHPREVIEW},
    )
    assert not image.support_level_overrides
    assert "SUPPORT_LEVEL_ARCH" not in DOCKERFILE_TEMPLATE.render(
        DOCKERFILE_RUN="RUN", image=image
    )


def test_support_level_overrides_kiwi():
    with pytest.raises(ValueError, match="needs a Dockerfile build"):
        DevelopmentContainer(
            **_BASE_KWARGS,
            build_recipe_type=BuildType.KIWI,
            support_level_overrides={Arch.AARCH64: SupportLevel.TECHPREVIEW},
        )
