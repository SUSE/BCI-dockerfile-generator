from bci_build.package import BuildType
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from bci_build.templates import SERVICE_TEMPLATE

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
            image=LanguageStackContainer(
                **_BASE_KWARGS, build_recipe_type=BuildType.KIWI
            )
        )
        == """<services>
  <service mode="buildtime" name="kiwi_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
</services>"""
    )


def test_service_with_replacement_kiwi():
    assert (
        SERVICE_TEMPLATE.render(
            image=LanguageStackContainer(
                **_BASE_KWARGS,
                build_recipe_type=BuildType.KIWI,
                replacements_via_service=[
                    Replacement(
                        regex_in_build_description="re", package_name="coreutils"
                    ),
                    Replacement(
                        regex_in_build_description="re",
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
    <param name="regex">re</param>
    <param name="package">coreutils</param>
  </service>
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">replacementfile</param>
    <param name="regex">re</param>
    <param name="package">coreutils</param>
  </service>
</services>"""
    )


def test_service_with_replacement_docker():
    assert (
        SERVICE_TEMPLATE.render(
            image=LanguageStackContainer(
                **_BASE_KWARGS,
                build_recipe_type=BuildType.DOCKER,
                replacements_via_service=[
                    Replacement(
                        regex_in_build_description="%%my_ver%%", package_name="sh"
                    ),
                    Replacement(
                        regex_in_build_description="%%minor_ver%%",
                        package_name="filesystem",
                        parse_version="minor",
                    ),
                    Replacement(
                        regex_in_build_description="%%minor_ver%%",
                        file_name="replacementfile",
                        package_name="filesystem",
                        parse_version="minor",
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
