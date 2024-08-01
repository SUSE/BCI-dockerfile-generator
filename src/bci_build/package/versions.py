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
           "Tumbleweed": "1.25.5",
           "6": "1.21.5",
           "5": "1.21.5"
       }
   }


The package versions are available via the function :py:func:`get_pkg_version`.

The json file is updated via the function :py:func:`run_version_update`. It can
also be called directly via :command:`poetry run update-versions` and is also
run in the CI via :file:`.github/workflows/update-versions.yml`. Note that
:py:func:`run_version_update` reads your OBS credentials from the environment
variables ``OSC_USER`` and ``OSC_PASSWORD``. The function fails if one of them
is not present.

To add a new package to the versions json, add it's package name and all code
streams with a dummy version, e.g.:

.. code-block:: json

   {
       "mariadb": {
           "Tumbleweed": "",
           "6": ""
       }
   }

Save the file and run the version update. :py:func:`update_versions` will fetch
the current version for every code stream that is present in the dictionary.

For some packages we do not need to know the full version, to prevent pointless
automated churn. In such a case, add the additional key ``version_format`` to a
package dictionary and set the value to the version format limit (e.g. `major`
or `minor`). The value must correspond to a enum value of
:py:class:`~bci_build.package.ParseVersion`. Applied to the above example, this
results in:

.. code-block:: json

   {
       "nginx": {
           "parse_version": "minor",
           "Tumbleweed": "1.25",
           "6": "1.21",
           "5": "1.21"
       }
   }


"""

import json
from pathlib import Path
from typing import Literal
from typing import NoReturn
from typing import TypedDict
from typing import overload
from xml.etree import ElementTree as ET

import requests
from packaging import version

from bci_build.package import OsVersion
from bci_build.package import ParseVersion

_VERS_FMT_KEY = "version_format"

_pkg_version_fields: dict[str, type[ParseVersion] | type[str]] = {
    _VERS_FMT_KEY: ParseVersion
}
for os_ver in OsVersion:
    _pkg_version_fields[str(os_ver)] = str

_PKG_VERSION_T = TypedDict("_PKG_VERSION_T", fields=_pkg_version_fields, total=False)


#: Type for storing versions of packages.
#: The key is the package name.
#: The value is a dictionary, where the key is the code stream and the value the
#: version of the package
_PACKAGE_VERSIONS_T = dict[str, _PKG_VERSION_T]

#: Path to the json file where the package versions are stored
PACKAGE_VERSIONS_JSON_PATH = Path(__file__).parent / "package_versions.json"


def _read_pkg_versions() -> _PACKAGE_VERSIONS_T:
    """Reads the package versions from the json file in
    :py:const:`~bci_build.package.versions.PACKAGE_VERSIONS_JSON_PATH`.

    """
    with open(PACKAGE_VERSIONS_JSON_PATH, "r") as versions_json:
        return json.load(versions_json)


#: versions of all packages where we have to hardcode the version
_PACKAGE_VERSIONS = _read_pkg_versions()


def get_pkg_version(pkg_name: str, os_version: OsVersion) -> str:
    if pkg_name not in _PACKAGE_VERSIONS:
        raise ValueError(f"Package {pkg_name} not tracked")

    if (k := str(os_version)) not in (pkg_vers := _PACKAGE_VERSIONS[pkg_name]):
        raise ValueError(f"OS Version {k} not tracked for package {pkg_name}")

    return pkg_vers[k]


#: projects from which to take package versions
_OBS_PROJECTS: dict[OsVersion, str] = {
    **{OsVersion(ver): f"SUSE:SLE-15-SP{ver}:Update" for ver in range(3, 8)},
    **{OsVersion.TUMBLEWEED: "openSUSE:Factory"},
}


@overload
def format_version(
    ver: str,
    format: Literal[ParseVersion.MAJOR, ParseVersion.MINOR, ParseVersion.PATCH],
) -> str: ...


@overload
def format_version(
    ver: str,
    format: Literal[ParseVersion.PATCH_UPDATE, ParseVersion.OFFSET],
) -> NoReturn: ...


def format_version(ver: str, format: ParseVersion) -> str:
    """Format the string `ver` to the supplied `format`, e.g.:

    >>> format_version('1.2.3', ParseVersion.MAJOR)
    1
    >>> format_version('1.2.3', ParseVersion.MINOR)
    1.2
    >>> format_version('1.2', ParseVersion.PATCH)
    1.2.0

    """
    v = version.parse(ver)
    match format:
        case ParseVersion.MAJOR:
            return str(v.major)
        case ParseVersion.MINOR:
            return f"{v.major}.{v.minor}"
        case ParseVersion.PATCH:
            return f"{v.major}.{v.minor}.{v.micro}"
        case _:
            raise ValueError(f"Invalid version format: {format}")


def fetch_package_version(prj: str, pkg: str) -> str:
    """Fetch the package information for the given package and project."""

    resp = requests.get(
        f"https://api.opensuse.org/public/source/{prj}/{pkg}",
        params={"view": "info", "parse": 1},
    )
    resp.raise_for_status()
    resp_xml = ET.fromstring(resp.content)
    return resp_xml.find("version").text


def update_versions() -> dict[str, dict[str, str]]:
    """Fetch all package versions from the build service and return the
    result. This function fetches all versions for every package and every code
    stream defined in :py:const:`~bci_build.package.versions.PACKAGE_VERSIONS`.

    """
    new_versions: dict[str, dict[str, str]] = {}

    def _fetch_version(
        pkg: str, os_version: OsVersion, version_format: ParseVersion
    ) -> None:
        new_versions[pkg][str(os_version)] = format_version(
            fetch_package_version(prj=_OBS_PROJECTS[os_version], pkg=pkg),
            version_format,
        )

    for pkg, versions in _PACKAGE_VERSIONS.items():
        new_versions[pkg] = {}

        constraint = versions.get(_VERS_FMT_KEY, ParseVersion.PATCH)
        for os_version in versions.keys():
            if os_version != _VERS_FMT_KEY:
                _fetch_version(pkg, OsVersion.parse(os_version), constraint)

        if _VERS_FMT_KEY in versions:
            new_versions[pkg][_VERS_FMT_KEY] = constraint

    return new_versions


def run_version_update() -> None:
    """Fetch the new package versions via :py:func:`update_versions` and write
    the result to the package versions json file.
    """
    new_versions = update_versions()
    with open(PACKAGE_VERSIONS_JSON_PATH, "w") as versions_json:
        json.dump(new_versions, versions_json, indent=4, sort_keys=True)
