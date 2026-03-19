from unittest.mock import patch

import pytest

from bci_build.os_version import OsVersion
from bci_build.package.versions import _OBS_PROJECTS
from bci_build.package.versions import format_version
from bci_build.package.versions import get_all_pkg_version
from bci_build.package.versions import get_pkg_version
from bci_build.package.versions import update_versions
from bci_build.util import ParseVersion


def fake_package_versions():
    return {
        "pkg1": {
            "latest": {
                "16.0": "1.0",
                "16.1": "1.0",
                "7": "1.0",
                "Tumbleweed": "1.5",
            },
            "version_format": "minor",
        },
        "pkg2": {
            "latest": {
                "16.0": "1.1.0",
                "Tumbleweed": "1.1.1",
            },
            "release_history": {
                "16.0": ["1.1.0"],
                "Tumbleweed": ["1.1.0", "1.1.1"],
            },
            "version_format": "patch",
        },
    }


def fake_fetch_package_version(prj: str, pkg: str) -> str:
    new_versions = {
        "pkg1": {
            _OBS_PROJECTS[OsVersion.parse("16.0")]: "1.5",
            _OBS_PROJECTS[OsVersion.parse("16.1")]: "1.5",
            _OBS_PROJECTS[OsVersion.parse("7")]: "1.5",
            _OBS_PROJECTS[OsVersion.parse("Tumbleweed")]: "2.0",
        },
        "pkg2": {
            _OBS_PROJECTS[OsVersion.parse("16.0")]: "1.1.1",
            _OBS_PROJECTS[OsVersion.parse("Tumbleweed")]: "1.2.0",
        },
    }

    return new_versions[pkg][prj]


def test_get_pkg_version():
    with patch(
        "bci_build.package.versions.get_package_versions",
        return_value=fake_package_versions(),
    ):
        assert get_pkg_version("pkg1", "Tumbleweed") == "1.5"
        assert get_pkg_version("pkg1", "16.0") == "1.0"

        assert get_pkg_version("pkg2", "Tumbleweed") == "1.1.1"
        assert get_pkg_version("pkg2", "16.0") == "1.1.0"


def test_get_all_pkg_version():
    with patch(
        "bci_build.package.versions.get_package_versions",
        return_value=fake_package_versions(),
    ):
        with pytest.raises(ValueError):
            get_all_pkg_version("pkg1", "Tumbleweed")
        with pytest.raises(ValueError):
            get_all_pkg_version("pkg1", "16.0")

        assert get_all_pkg_version("pkg2", "Tumbleweed") == ["1.1.0", "1.1.1"]
        assert get_all_pkg_version("pkg2", "16.0") == ["1.1.0"]


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

            assert new_versions["pkg1"]["latest"]["Tumbleweed"] == "2.0"
            assert new_versions["pkg1"]["latest"]["16.0"] == "1.5"

            assert new_versions["pkg2"]["latest"]["Tumbleweed"] == "1.2.0"
            assert new_versions["pkg2"]["latest"]["16.0"] == "1.1.1"
            assert new_versions["pkg2"]["release_history"]["Tumbleweed"] == [
                "1.1.0",
                "1.1.1",
                "1.2.0",
            ]
            assert new_versions["pkg2"]["release_history"]["16.0"] == [
                "1.1.0",
                "1.1.1",
            ]


def test_format_version():
    assert format_version("1.2.3", ParseVersion.MAJOR) == "1"
    assert format_version("1.2.3", ParseVersion.MINOR) == "1.2"
    assert format_version("1.2.3", ParseVersion.PATCH) == "1.2.3"

    assert format_version("1.2.3+64845ffd9", ParseVersion.MAJOR) == "1"
    assert format_version("1.2.3+64845ffd9", ParseVersion.MINOR) == "1.2"
    assert format_version("1.2.3+64845ffd9", ParseVersion.PATCH) == "1.2.3"
