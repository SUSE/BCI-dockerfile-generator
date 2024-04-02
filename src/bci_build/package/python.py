"""Python language related BCI containers"""

import datetime
from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import _SUPPORTED_UNTIL_SLE
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel


def _get_python_kwargs(
    py3_ver: Literal["3.6", "3.9", "3.10", "3.11", "3.12"], os_version: OsVersion
):
    is_system_py: bool = py3_ver == (
        "3.6" if os_version != OsVersion.TUMBLEWEED else "3.11"
    )
    py3_ver_nodots = py3_ver.replace(".", "")

    py3 = (
        "python3"
        if is_system_py and os_version != OsVersion.TUMBLEWEED
        else f"python{py3_ver_nodots}"
    )
    py3_ver_replacement = f"%%py{py3_ver_nodots}_ver%%"
    pip3 = f"{py3}-pip"
    pip3_replacement = "%%pip_ver%%"
    has_pipx = False
    # Tumbleweed rocks
    if os_version == OsVersion.TUMBLEWEED:
        has_pipx = True
    # Enabled only for Python 3.11 on SLE15 (jsc#PED-5573)
    if os_version not in (OsVersion.BASALT, OsVersion.TUMBLEWEED) and py3_ver == "3.11":
        has_pipx = True

    kwargs = {
        "name": "python",
        "pretty_name": f"Python {py3_ver} development",
        "version": py3_ver,
        "additional_versions": ["3"],
        "env": {
            "PYTHON_VERSION": py3_ver_replacement,
            "PATH": "$PATH:/root/.local/bin",
            "PIP_VERSION": pip3_replacement,
        },
        "package_list": [f"{py3}-devel", py3, pip3, "curl", "git-core"]
        + (
            [f"{py3}-wheel"]
            if is_system_py or os_version == OsVersion.TUMBLEWEED
            else []
        )
        + ([f"{py3}-pipx"] if has_pipx else [])
        + os_version.lifecycle_data_pkg,
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=py3_ver_replacement,
                package_name=f"{py3}-base",
            ),
            Replacement(regex_in_build_description=pip3_replacement, package_name=pip3),
        ],
        "os_version": os_version,
    }

    config_sh_script = "install -d -m 0755 /root/.local/bin"

    if not is_system_py:
        config_sh_script += rf"""; ln -s /usr/bin/python{py3_ver} /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc{py3_ver} /usr/local/bin/pydoc"""

    kwargs["config_sh_script"] = config_sh_script

    return kwargs


PYTHON_3_6_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs("3.6", os_version),
        package_name="python-3.6-image",
        support_level=SupportLevel.L3,
    )
    for os_version in (OsVersion.SP5, OsVersion.SP6)
)

_PYTHON_TW_VERSIONS = ("3.10", "3.12", "3.11")
PYTHON_TW_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs(pyver, OsVersion.TUMBLEWEED),
        is_latest=pyver == _PYTHON_TW_VERSIONS[-1],
        package_name=f"python-{pyver}-image",
    )
    for pyver in _PYTHON_TW_VERSIONS
)

PYTHON_3_11_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs("3.11", os_version),
        package_name="python-3.11-image",
        support_level=SupportLevel.L3,
        # https://peps.python.org/pep-0664/ defines 2027/10/31, SUSE offers until end of the year
        supported_until=datetime.date(2027, 12, 31),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
    )
    for os_version in (OsVersion.SP5, OsVersion.SP6)
)

PYTHON_3_12_CONTAINERS = LanguageStackContainer(
    **_get_python_kwargs("3.12", OsVersion.SP6),
    package_name="python-3.12-image",
    support_level=SupportLevel.L3,
    supported_until=_SUPPORTED_UNTIL_SLE[OsVersion.SP6],
    # Technically it is the latest but we want to prefer the long term Python 3.11
    is_latest=False,
)
