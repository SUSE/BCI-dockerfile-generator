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
            "codestreams": {
                "16.0": {
                    "latest": "1.27"
                },
                "7": {
                    "latest": "1.21"
                },
                "Tumbleweed": {
                    "latest": "1.29"
                }
            },
            "track_versions": false,
            "version_format": "minor"
        }
   }

The key ``version_format`` sets the value to the version format limit
(e.g. `major` or `minor`). The value must correspond to a enum value of
:py:class:`~bci_build.package.ParseVersion`.

The key ``track_versions`` enables tracking all versions of a given package.

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
            "codestreams": {
                "Tumbleweed": "",
                "6": ""
            }
       }
   }

Save the file and run the version update. :py:func:`update_versions` will fetch
the current version for every code stream that is present in the dictionary.

"""

import json
import re
import xml.etree.ElementTree as ET
from functools import cache
from functools import cmp_to_key
from pathlib import Path
from typing import Dict
from typing import List
from typing import TypedDict

import requests
from version_utils import rpm

from bci_build.container_attributes import Arch
from bci_build.os_version import OsVersion
from bci_build.util import ParseVersion


class CodestreamInfo(TypedDict, total=False):
    latest: str
    versions: List[str]


class PackageInfo(TypedDict, total=False):
    codestreams: Dict[str, CodestreamInfo]
    track_versions: bool
    version_format: str
    package_arch: str


PackageVersions = Dict[str, PackageInfo]

#: Path to the json file where the package versions are stored
PACKAGE_VERSIONS_JSON_PATH = Path(__file__).parent / "package_versions.json"

_VER_RE = r"""
^
(?P<major>\d+)                                             # major version
(?:\.(?P<minor>\d+))?                                      # minor version
(?:\.(?P<patch>\d+))?                                      # patch version
(?:\.(?P<update>\d+))?                                     # update version
(?P<pre>[a-zA-Z]+[0-9]*|~[a-zA-Z0-9]+)?                    # pre release name e.g. rc1, beta1, ~alpha1, ~rc2
(?:(\~|\+)(?P<scm>[a-zA-Z0-9.]+))?                         # scm revision e.g. +git5, +git5.g9265358, +svn592
(?:-(?P<release>[0-9]+(?:\.[0-9]+)*?)\.(?P<build>[0-9]+))? # rpm release e.g. 150700.53.31.1
$
"""

_VERSION_RE = re.compile(_VER_RE, re.VERBOSE)


@cache
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

    if (k := str(os_version)) not in (
        pkg_vers := package_versions[pkg_name]["codestreams"]
    ):
        raise ValueError(
            f"OS Version '{k}' not tracked for package '{pkg_name}' in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    return pkg_vers[k]["latest"]


def get_all_pkg_version(pkg_name: str, os_version: OsVersion) -> str:
    package_versions = get_package_versions()

    if pkg_name not in package_versions:
        raise ValueError(
            f"Package '{pkg_name}' not tracked in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    if (k := str(os_version)) not in (
        pkg_vers := package_versions[pkg_name]["codestreams"]
    ):
        raise ValueError(
            f"OS Version '{k}' not tracked for package '{pkg_name}' in '{PACKAGE_VERSIONS_JSON_PATH}'"
        )

    return pkg_vers[k].get("versions", [pkg_vers[k]["latest"]])


#: projects from which to take package versions
_OBS_PROJECTS: dict[OsVersion, str] = {
    OsVersion.SL16_0: "SUSE:SLFO:1.2",
    OsVersion.SL16_1: "SUSE:SLFO:Main",
    OsVersion.TUMBLEWEED: "openSUSE:Factory",
} | {OsVersion(ver): f"SUSE:SLE-15-SP{ver}:Update" for ver in range(4, 8)}


def format_version(version: str, format: ParseVersion) -> str:
    """Format the string `ver` to the supplied `format`, e.g.:

    >>> format_version('1.2.3', ParseVersion.MAJOR)
    1
    >>> format_version('1.2.3', ParseVersion.MINOR)
    1.2
    >>> format_version('1.2', ParseVersion.PATCH)
    1.2.0

    """
    m = _VERSION_RE.match(version)

    if not m:
        raise ValueError(f"Failed to parse: {version}")

    major = m.group("major") or "0"
    minor = m.group("minor") or "0"
    patch = m.group("patch") or "0"
    update = m.group("update") or "0"
    release = m.group("release") or "1"
    build = m.group("build") or "1"

    match format:
        case ParseVersion.MAJOR:
            return major
        case ParseVersion.MINOR:
            return f"{major}.{minor}"
        case ParseVersion.PATCH:
            return f"{major}.{minor}.{patch}"
        case ParseVersion.PATCH_UPDATE:
            return f"{major}.{minor}.{patch}.{update}"
        case ParseVersion.RELEASE:
            return f"{major}.{minor}.{patch}-{release}"
        case ParseVersion.RELEASE_INCREMENT:
            return f"{major}.{minor}.{patch}-{release}.{build}"
        case _:
            raise ValueError(f"Invalid version format: {format}")


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

    for pkg_name, pkg_info in package_versions.items():
        codestreams: dict[str, CodestreamInfo] = pkg_info["codestreams"]
        version_format: ParseVersion = ParseVersion(pkg_info["version_format"])
        pkg_arch: Arch = Arch(pkg_info.get("package_arch", "x86_64"))

        for os_version, _ in codestreams.items():
            pkg_version: str = fetch_package_version(
                version_format, OsVersion.parse(os_version), pkg_name, pkg_arch
            )

            new_version: str = format_version(pkg_version, version_format)
            codestreams[os_version]["latest"] = new_version

            if pkg_info.get("track_versions", False):
                if "versions" in codestreams[os_version]:
                    if new_version not in codestreams[os_version]["versions"]:
                        codestreams[os_version]["versions"].append(new_version)
                else:
                    codestreams[os_version]["versions"] = [new_version]

    return package_versions


def run_version_update() -> None:
    """Fetch the new package versions via :py:func:`update_versions` and write
    the result to the package versions json file.

    """
    data: PackageVersions = update_versions()

    with open(PACKAGE_VERSIONS_JSON_PATH, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)
