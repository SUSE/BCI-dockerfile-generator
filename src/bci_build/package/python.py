"""Python language related BCI containers"""

import datetime
from dataclasses import dataclass
from typing import Literal

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_PYTHON_VERSIONS = Literal["3.6", "3.9", "3.10", "3.11", "3.12", "3.13"]

# The lifecycle is handcrafted by the SUSE Python maintainers
_SLE_15_PYTHON_SUPPORT_ENDS: dict[_PYTHON_VERSIONS, datetime.date | None] = {
    # Actually end of general support of SLE15, SP7 is the last known SP
    "3.6": _SUPPORTED_UNTIL_SLE[OsVersion.SP7],
    # per jsc#PED-10823
    "3.9": datetime.datetime(2027, 12, 31),
    # only openSUSE
    "3.10": None,
    # https://peps.python.org/pep-0664/ defines 2027/10/31, SUSE offers additional 2 years
    "3.11": datetime.date(2029, 12, 31),
    # see jsc#PED-12365 - maybe superseded by 3.14/3.15
    "3.13": datetime.date(2026, 12, 31),
}


@dataclass
class PythonDevelopmentContainer(DevelopmentContainer):
    has_pipx: bool = False
    has_wheel: bool = False


def _system_python(os_version: OsVersion) -> _PYTHON_VERSIONS:
    return "3.6" if os_version.is_sle15 else "3.13"


def _get_python_kwargs(py3_ver: _PYTHON_VERSIONS, os_version: OsVersion):
    is_system_py: bool = py3_ver == _system_python(os_version)
    py3_ver_nodots = py3_ver.replace(".", "")

    py3 = (
        "python3" if is_system_py and os_version.is_sle15 else f"python{py3_ver_nodots}"
    )
    py3_ver_replacement = f"%%py{py3_ver_nodots}_ver%%"
    pip3 = f"{py3}-pip"
    pip3_replacement = "%%pip_ver%%"
    has_wheel = has_pipx = False
    py_env = {
        "PYTHON_VERSION": py3_ver_replacement,
        "PIP_VERSION": pip3_replacement,
    }

    if os_version.is_tumbleweed:
        # Tumbleweed rocks
        has_pipx = has_wheel = True
    elif os_version.is_sle15:
        if py3_ver not in ("3.6", "3.9"):
            # Enabled only for Python 3.11+ on SLE15 (jsc#PED-5573)
            has_pipx = True
        # py3.12 pending discussion
        if py3_ver not in ("3.12", "3.9"):
            has_wheel = True
    elif os_version.is_sl16:
        has_pipx = has_wheel = True

    if has_pipx:
        py_env = py_env | {
            "PIPX_HOME": "/usr/local/lib/pipx",
            "PIPX_BIN_DIR": "/usr/local/bin",
            "PIPX_MAN_DIR": "/usr/local/man",
        }

    kwargs = {
        "name": "python",
        "pretty_name": f"Python {py3_ver} development",
        "version": py3_ver_replacement,
        "tag_version": py3_ver,
        "env": py_env,
        "package_list": (
            [f"{py3}-devel", py3, pip3]
            + os_version.common_devel_packages
            + ([f"{py3}-wheel"] if has_wheel else [])
            + ([f"{py3}-pipx"] if has_pipx else [])
            + (["lifecycle-data-sle-module-python3"] if os_version.is_sle15 else [])
            + os_version.lifecycle_data_pkg
        ),
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=py3_ver_replacement,
                package_name=f"{py3}-base",
            ),
            Replacement(regex_in_build_description=pip3_replacement, package_name=pip3),
        ],
        "has_wheel": has_wheel,
        "has_pipx": has_pipx,
        "os_version": os_version,
        "support_level": SupportLevel.L3,
        "supported_until": (
            _SLE_15_PYTHON_SUPPORT_ENDS[py3_ver] if os_version.is_sle15 else None
        ),
        "min_release_counter": {
            OsVersion.SP7: 70,
        },
    }

    config_sh_script = ""

    if not is_system_py:
        config_sh_script += rf"""if test -x /usr/bin/python3; then echo 'is_system_py is wrong - report a bug'; exit 1; fi; \
    ln -s /usr/bin/python{py3_ver} /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc{py3_ver} /usr/local/bin/pydoc"""

    # broken packaging without a "pip" update-alternatives link
    if py3_ver in ("3.9",):
        config_sh_script += (
            f"; test -e /usr/bin/pip || ln -s /usr/bin/pip{py3_ver} /usr/local/bin/pip"
        )

    kwargs["config_sh_script"] = config_sh_script

    return kwargs


PYTHON_3_6_CONTAINERS = (
    PythonDevelopmentContainer(
        **_get_python_kwargs("3.6", os_version),
        package_name="python-3.6-image",
        additional_versions=["3"],
    )
    for os_version in (OsVersion.SP7,)
)


_PYTHON_TW_VERSIONS: tuple[_PYTHON_VERSIONS, ...] = ("3.11", "3.12", "3.13")
PYTHON_TW_CONTAINERS = (
    PythonDevelopmentContainer(
        **_get_python_kwargs(pyver, OsVersion.TUMBLEWEED),
        is_latest=pyver == _PYTHON_TW_VERSIONS[-1],
        package_name=f"python-{pyver}-image",
        additional_versions=["3"],
    )
    for pyver in _PYTHON_TW_VERSIONS
)

PYTHON_3_11_CONTAINERS = (
    PythonDevelopmentContainer(
        **_get_python_kwargs("3.11", os_version),
        package_name="python-3.11-image",
        additional_versions=["3"],
    )
    for os_version in (OsVersion.SP7,)
)

PYTHON_3_13_CONTAINERS = [
    PythonDevelopmentContainer(
        **_get_python_kwargs("3.13", os_version),
        package_name="python-3.13-image",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        additional_versions=["3"],
    )
    for os_version in (OsVersion.SP7, OsVersion.SL16_0)
]

_CI_PYTHON = ("3.13", "313")


BCI_CI_CONTAINERS = [
    DevelopmentContainer(
        name="bci-ci",
        pretty_name="BCI-internal CI",
        version=(python_ver := "%%python_version%%"),
        tag_version="3",
        is_singleton_image=True,
        version_in_uid=False,
        os_version=os_version,
        from_image=generate_from_image_tag(os_version, "python"),
        is_latest=True,
        support_level=SupportLevel.UNSUPPORTED,
        package_list=(
            "build",
            "buildah",
            "dnf",
            "fish",
            "gcc",
            "git-core",
            "jq",
            "osc",
            "patch",
            "python3-devel",
            "python3-dnf",
            "python3-pipx",
            "python3-poetry",
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description=python_ver,
                package_name="python313-base",
                parse_version=ParseVersion.PATCH,
            )
            for ver in (ParseVersion.MAJOR, ParseVersion.MINOR)
        ],
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
