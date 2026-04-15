"""This module contains a simple mechanism to store the package versions for
various code streams in a json file.

We need to know the version of certain packages in the distribution to be able
to hardcode it in READMEs as we cannot let the build service create READMEs for
us (this is a hard to work around limitation of OBS and the
`replace_using_package_version
<https://github.com/openSUSE/obs-service-replace_using_package_version>`_
service).

Therefore we keep a single json file in the code with all packages and their
version per code stream in the git repository of the following form:

.. code-block:: json

   {
        "nginx": {
            "latest": {
                "16.0": "1.27",
                "7": "1.21",
                "Tumbleweed": "1.29"
            },
            "release_history": {
                "16.0": ["1.27"],
                "7": ["1.21"],
                "Tumbleweed": ["1.29", 1.28, 1.27]
            },
            "version_format": "minor"
        }
   }

The key ``version_format`` sets the value to the version format limit
(e.g. `major` or `minor`). The value must correspond to a enum value of
:py:class:`~bci_build.package.ParseVersion`.

The latest package version is available via the function
:py:func:`get_pkg_version` and all versions via :py:func:`get_all_pkg_version`.

The json file is updated via the function :py:func:`run_version_update`. It can
also be called directly via :command:`poetry run update-versions` and is also
run in the CI via :file:`.github/workflows/update-versions.yml`.

To add a new package to the versions json, add it's package name and all code
streams with a dummy version, e.g.:

.. code-block:: json

   {
       "mariadb": {
            "latest": {
                "Tumbleweed": "",
                "6": ""
            }
       }
   }

Save the file and run the version update. :py:func:`update_versions` will fetch
the current version for every code stream that is present in the dictionary.

"""

import json
import xml.etree.ElementTree as ET
from functools import cmp_to_key
from pathlib import Path
from typing import Dict
from typing import List
from typing import TypedDict

import requests
from packaging import version
from version_utils import rpm

from bci_build.container_attributes import Arch
from bci_build.os_version import OsVersion
from bci_build.util import ParseVersion


class PackageInfo(TypedDict, total=False):
    latest: Dict[str, str]
    release_history: Dict[str, List[str]]
    version_format: str
    package_arch: str


PackageVersions = Dict[str, PackageInfo]

#: Path to the json file where the package versions are stored
PACKAGE_VERSIONS_JSON_PATH = Path(__file__).parent / "package_versions.json"


def get_package_versions() -> PackageVersions:
    """Reads the package versions from the json file in
    :py:const:`~bci_build.package.versions.PACKAGE_VERSIONS_JSON_PATH`.

    """
    with open(PACKAGE_VERSIONS_JSON_PATH) as versions_json:
        return json.load(versions_json)


def get_pkg_version(pkg_name: str, os_version: OsVersion) -> str:
    package_versions = get_package_versions()

    if pkg_name not in package_versions:
        raise ValueError(
            f"Package '{pkg_name}' not tracked in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    if (k := str(os_version)) not in (pkg_vers := package_versions[pkg_name]["latest"]):
        raise ValueError(
            f"OS Version '{k}' not tracked for package '{pkg_name}' in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    return pkg_vers[k]


def get_all_pkg_version(pkg_name: str, os_version: OsVersion) -> str:
    package_versions = get_package_versions()

    if pkg_name not in package_versions:
        raise ValueError(
            f"Package '{pkg_name}' not tracked in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    if (k := str(os_version)) not in (
        pkg_vers := package_versions[pkg_name].get("release_history", {})
    ):
        raise ValueError(
            f"OS Version '{k}' not tracked for package '{pkg_name}' in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    return pkg_vers[k]


#: projects from which to take package versions
_OBS_PROJECTS: dict[OsVersion, str] = {
    OsVersion.SL16_0: "SUSE:SLFO:1.2",
    OsVersion.SL16_1: "SUSE:SLFO:Main",
    OsVersion.TUMBLEWEED: "openSUSE:Factory",
} | {OsVersion(ver): f"SUSE:SLE-15-SP{ver}:Update" for ver in range(4, 8)}


def format_version(package_version: str, version_format: ParseVersion) -> str:
    """Format the string `package_version` to the supplied `version_format`, e.g.:

    >>> format_version('1.2.3', ParseVersion.MAJOR)
    1
    >>> format_version('1.2.3', ParseVersion.MINOR)
    1.2
    >>> format_version('1.2', ParseVersion.PATCH)
    1.2.0

    """
    if "-" in package_version:
        base, rel = package_version.rsplit("-", 1)
        release, build = rel.rsplit(".", 1)
    else:
        base, release, build = package_version, "1", "1"

    v = version.parse(base.replace(":", "!").partition("~")[0])
    update = v.release[3] if len(v.release) >= 4 else 0

    match version_format:
        case ParseVersion.MAJOR:
            return f"{v.major}"
        case ParseVersion.MINOR:
            return f"{v.major}.{v.minor}"
        case ParseVersion.PATCH:
            return f"{v.major}.{v.minor}.{v.micro}"
        case ParseVersion.PATCH_UPDATE:
            return f"{v.major}.{v.minor}.{v.micro}.{update}"
        case ParseVersion.RELEASE:
            return f"{v.major}.{v.minor}.{v.micro}-{release}"
        case ParseVersion.RELEASE_INCREMENT:
            return f"{v.major}.{v.minor}.{v.micro}-{release}.{build}"
        case _:
            raise ValueError(f"Invalid version format: {version_format}")


def fetch_package_version_from_obs(os_version: OsVersion, package: str) -> str:
    """Fetch the package version from the OBS API and return it."""
    project = _OBS_PROJECTS[os_version]
    try:
        res = requests.get(
            f"https://api.opensuse.org/public/source/{project}/{package}",
            params={"view": "info", "parse": "1"},
            headers={"User-Agent": "BCI update-versions"},
        )
        res.raise_for_status()

        el = ET.fromstring(res.text)
        return el.findtext("version")
    except Exception as e:
        raise ValueError(
            f"Failed to get package version from OBS for '{project}/{package}': {str(e)}"
        )


def find_scc_product_id(os_version: OsVersion, arch: Arch):
    """Fetch the SCC product for a given version/arch from the SCC API and return it."""
    if os_version == OsVersion.TUMBLEWEED:
        raise ValueError("Tumbleweed is not a registered SCC product")

    res = requests.get(
        "https://scc.suse.com/api/package_search/products",
        headers={"User-Agent": "BCI update-versions"},
    )

    res.raise_for_status()
    products = res.json()["data"]
    identifier = f"SLES/{os_version.os_version}/{arch}"

    for p in products:
        if p["identifier"] == identifier:
            return p["id"]

    raise ValueError(f"SCC product not found: {identifier}")


def fetch_package_versions_from_scc(
    os_version: OsVersion, package: str, arch: Arch
) -> list[str]:
    """Fetch the package version from the SCC API and return it."""
    product = find_scc_product_id(os_version, arch)
    try:
        res = requests.get(
            f"https://scc.suse.com/api/package_search/packages?product_id={product}&query={package}",
            headers={"User-Agent": "BCI update-versions"},
        )

        res.raise_for_status()
        packages = res.json()["data"]

        versions = [
            f"{pkg['version']}-{pkg['release']}"
            for pkg in packages
            if pkg["name"] == package
        ]
        return sorted(versions, key=cmp_to_key(lambda a, b: rpm.compare_versions(a, b)))
    except Exception as e:
        raise ValueError(
            f"Failed to get package version from SCC for '{os_version.os_version}/{arch}/{package}': {str(e)}"
        )


def fetch_package_version(
    version_format: ParseVersion, os_version: str, package: str, arch: Arch
):
    if version_format in {ParseVersion.RELEASE, ParseVersion.RELEASE_INCREMENT}:
        return fetch_package_versions_from_scc(os_version, package, arch)[-1]
    else:
        return fetch_package_version_from_obs(os_version, package)


def update_versions() -> dict[str, dict[str, str]]:
    """Fetch all package versions from the build service and return the
    result. This function fetches all versions for every package and every code
    stream defined in :py:const:`~bci_build.package.versions.PACKAGE_VERSIONS`.

    """
    package_versions = get_package_versions()

    for pkg_name in package_versions.keys():
        pkg_info = package_versions[pkg_name]
        version_format: ParseVersion = ParseVersion(pkg_info["version_format"])
        pkg_arch: Arch = Arch(pkg_info.get("package_arch", "x86_64"))

        for os_version in pkg_info["latest"].keys():
            pkg_version: str = fetch_package_version(
                version_format, OsVersion.parse(os_version), pkg_name, pkg_arch
            )

            new_version = format_version(pkg_version, version_format)
            pkg_info["latest"][os_version] = new_version

            if "release_history" in pkg_info:
                if os_version in pkg_info["release_history"]:
                    if new_version not in pkg_info["release_history"][os_version]:
                        pkg_info["release_history"][os_version].append(new_version)
                else:
                    pkg_info["release_history"][os_version] = [new_version]

    return package_versions


def run_version_update() -> None:
    """Fetch the new package versions via :py:func:`update_versions` and write
    the result to the package versions json file.

    """
    data: PackageVersions = update_versions()

    with open(PACKAGE_VERSIONS_JSON_PATH, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)
