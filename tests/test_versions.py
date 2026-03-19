from unittest.mock import patch

from bci_build.container_attributes import Arch
from bci_build.os_version import OsVersion
from bci_build.package.versions import format_version
from bci_build.package.versions import get_all_pkg_version
from bci_build.package.versions import get_pkg_version
from bci_build.package.versions import update_versions
from bci_build.util import ParseVersion


def fake_package_versions():
    return {
        "pkg1": {
            "codestreams": {
                "16.0": {
                    "latest": "1.0",
                },
                "16.1": {
                    "latest": "1.0",
                },
                "7": {
                    "latest": "1.0",
                },
                "Tumbleweed": {
                    "latest": "1.5",
                },
            },
            "track_versions": False,
            "version_format": "minor",
        },
        "pkg2": {
            "codestreams": {
                "16.0": {
                    "latest": "1.1.0",
                    "versions": ["1.1.0"],
                },
                "Tumbleweed": {
                    "latest": "1.1.1",
                    "versions": ["1.1.0", "1.1.1"],
                },
            },
            "track_versions": True,
            "version_format": "patch",
        },
        "pkg3": {
            "codestreams": {
                "16.0": {
                    "latest": "6.12.0-160000.26",
                    "versions": [
                        "6.12.0-160000.5",
                        "6.12.0-160000.6",
                        "6.12.0-160000.7",
                        "6.12.0-160000.8",
                        "6.12.0-160000.9",
                        "6.12.0-160000.26",
                    ],
                },
            },
            "track_versions": True,
            "version_format": "release",
        },
    }


def fake_fetch_package_version(
    version_format: ParseVersion, os_version: str, package: str, arch: Arch
) -> str:
    new_versions = {
        "pkg1": {
            OsVersion.SL16_0: "1.5",
            OsVersion.SL16_1: "1.5",
            OsVersion.SP7: "1.5",
            OsVersion.TUMBLEWEED: "2.0",
        },
        "pkg2": {
            OsVersion.SL16_0: "1.1.1",
            OsVersion.TUMBLEWEED: "1.2.0",
        },
        "pkg3": {
            OsVersion.SL16_0: "6.12.0-160000.26.1",
        },
    }

    return new_versions[package][os_version]


def test_get_pkg_version():
    with patch(
        "bci_build.package.versions.get_package_versions",
        return_value=fake_package_versions(),
    ):
        assert get_pkg_version("pkg1", "Tumbleweed") == "1.5"
        assert get_pkg_version("pkg1", "16.0") == "1.0"

        assert get_pkg_version("pkg2", "Tumbleweed") == "1.1.1"
        assert get_pkg_version("pkg2", "16.0") == "1.1.0"

        assert get_pkg_version("pkg3", "16.0") == "6.12.0-160000.26"


def test_get_all_pkg_version():
    with patch(
        "bci_build.package.versions.get_package_versions",
        return_value=fake_package_versions(),
    ):
        assert get_all_pkg_version("pkg1", "Tumbleweed") == ["1.5"]
        assert get_all_pkg_version("pkg1", "16.0") == ["1.0"]

        assert get_all_pkg_version("pkg2", "Tumbleweed") == ["1.1.0", "1.1.1"]
        assert get_all_pkg_version("pkg2", "16.0") == ["1.1.0"]

        assert get_all_pkg_version("pkg3", "16.0") == [
            "6.12.0-160000.5",
            "6.12.0-160000.6",
            "6.12.0-160000.7",
            "6.12.0-160000.8",
            "6.12.0-160000.9",
            "6.12.0-160000.26",
        ]


def test_update_versions():
    with patch(
        "bci_build.package.versions.get_package_versions",
        return_value=fake_package_versions(),
    ):
        with patch(
            "bci_build.package.versions.fetch_package_version",
            side_effect=fake_fetch_package_version,
        ):
            new_versions = update_versions()

            assert new_versions["pkg1"]["codestreams"]["Tumbleweed"]["latest"] == "2.0"
            assert new_versions["pkg1"]["codestreams"]["16.0"]["latest"] == "1.5"

            assert (
                new_versions["pkg2"]["codestreams"]["Tumbleweed"]["latest"] == "1.2.0"
            )
            assert new_versions["pkg2"]["codestreams"]["16.0"]["latest"] == "1.1.1"
            assert new_versions["pkg2"]["codestreams"]["Tumbleweed"]["versions"] == [
                "1.1.0",
                "1.1.1",
                "1.2.0",
            ]
            assert new_versions["pkg2"]["codestreams"]["16.0"]["versions"] == [
                "1.1.0",
                "1.1.1",
            ]


def test_format_version():
    v = "1"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.0"
    assert format_version(v, ParseVersion.PATCH) == "1.0.0"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.0.0.0"
    assert format_version(v, ParseVersion.RELEASE) == "1.0.0-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.0.0-1.1"

    v = "1.2"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.0"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.0.0"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.0-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.0-1.1"

    v = "1.2.3"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.3"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.3.0"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.3-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.3-1.1"

    v = "1.2.3~alpha1"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.3"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.3.0"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.3-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.3-1.1"

    v = "1.2.3beta2"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.3"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.3.0"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.3-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.3-1.1"

    v = "1.2.3.50+g994fd9e0cc"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.3"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.3.50"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.3-1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.3-1.1"

    v = "3.0.6~git86.dce421a0d-160000.1.1"
    assert format_version(v, ParseVersion.MAJOR) == "3"
    assert format_version(v, ParseVersion.MINOR) == "3.0"
    assert format_version(v, ParseVersion.PATCH) == "3.0.6"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "3.0.6.0"
    assert format_version(v, ParseVersion.RELEASE) == "3.0.6-160000.1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "3.0.6-160000.1.1"

    v = "1.2.3.50+git994fd9e0cc-150700.0.1.1"
    assert format_version(v, ParseVersion.MAJOR) == "1"
    assert format_version(v, ParseVersion.MINOR) == "1.2"
    assert format_version(v, ParseVersion.PATCH) == "1.2.3"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "1.2.3.50"
    assert format_version(v, ParseVersion.RELEASE) == "1.2.3-150700.0.1"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "1.2.3-150700.0.1.1"

    v = "6.4.0-150700.53.31.1"
    assert format_version(v, ParseVersion.MAJOR) == "6"
    assert format_version(v, ParseVersion.MINOR) == "6.4"
    assert format_version(v, ParseVersion.PATCH) == "6.4.0"
    assert format_version(v, ParseVersion.PATCH_UPDATE) == "6.4.0.0"
    assert format_version(v, ParseVersion.RELEASE) == "6.4.0-150700.53.31"
    assert format_version(v, ParseVersion.RELEASE_INCREMENT) == "6.4.0-150700.53.31.1"
