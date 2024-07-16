"""This module contains a simple mechanism to store the package versions for
various code streams in a json file.

We need to know the version of certain packages in the distribution to be able
to hardcode it in READMEs as we cannot let the build service create READMEs for
us (this is a hard to work around limitation of OBS and the
replace_using_package_version service).

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

"""

import asyncio
import json
from pathlib import Path
from typing import Literal
from typing import NoReturn
from typing import overload

from packaging import version
from py_obs.osc import Osc
from py_obs.project import fetch_package_info

from bci_build.package import OsVersion
from bci_build.package import ParseVersion

#: Type for storing versions of packages.
#: The key is the package name.
#: The value is a dictionary, where the key is the code stream and the value the
#: version of the package
_PACKAGE_VERSIONS_T = dict[str, dict[str, str]]


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


def to_major_minor_version(ver: str) -> str:
    """Convert a valid python packaging version to ``$major.$minor`` form
    (dropping patch and further release details).

    """
    return f"{(v := version.parse(ver)).major}.{v.minor}"


def to_major_version(ver: str) -> str:
    """Return the major version of a valid python packaging version."""
    return str(version.parse(ver).major)


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


async def update_versions(osc: Osc) -> dict[str, dict[str, str]]:
    """Fetch all package versions from the build service and return the
    result. This function fetches all versions for every package and every code
    stream defined in :py:const:`~bci_build.package.versions.PACKAGE_VERSIONS`.

    """
    tasks = []
    new_versions: dict[str, dict[str, str]] = {}

    async def _fetch_version(pkg: str, os_version: OsVersion) -> None:
        new_versions[pkg][str(os_version)] = (
            await fetch_package_info(osc, prj=_OBS_PROJECTS[os_version], pkg=pkg)
        ).version

    for pkg, versions in _PACKAGE_VERSIONS.items():
        new_versions[pkg] = {}

        for os_version in versions.keys():
            tasks.append(_fetch_version(pkg, OsVersion.parse(os_version)))

    await asyncio.gather(*tasks)

    return new_versions


def run_version_update() -> None:
    """Fetch the new package versions via :py:func:`update_versions` and write
    the result to the package versions json file.

    This function reads in your OBS credentials from the mandatory environment
    variables ``OSC_USER`` and ``OSC_PASSWORD``.

    """
    osc = Osc.from_env()

    loop = asyncio.get_event_loop()

    try:
        new_versions = loop.run_until_complete(update_versions(osc))
    finally:
        loop.run_until_complete(osc.teardown())

    with open(PACKAGE_VERSIONS_JSON_PATH, "w") as versions_json:
        json.dump(new_versions, versions_json, indent=4, sort_keys=True)
