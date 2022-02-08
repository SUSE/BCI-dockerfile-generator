import asyncio
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Dict, List, Literal

import aiohttp
from bci_build.data import (
    DEFAULT_SLE_SERVICE_PACK,
    DEFAULT_SLE_VERSION,
    SUPPORTED_SLE_SERVICE_PACKS,
    SUPPORTED_SLE_VERSIONS,
)
from rpm_vercmp import vercmp


@dataclass
class SccProduct:
    """A product as returned by the SCC API.

    See also: `api docs <https://scc.suse.com/api/package_search/v4/documentation#/>`_
    """

    id: int
    name: str
    identifier: str
    type: str
    free: bool
    edition: str
    architecture: str


@dataclass
class SccPackage:
    """A SLE package as returned by the SCC API.

    See also: `api docs <https://scc.suse.com/api/package_search/v4/documentation#/>`_
    """

    id: int
    name: str
    arch: str
    version: str
    release: str
    products: List[SccProduct]

    def __post_init__(self) -> None:
        new_products = []
        for prod in self.products:
            if isinstance(prod, dict):
                new_products.append(SccProduct(**prod))
            else:
                new_products.append(prod)
        self.products = new_products


async def get_pkgs_from_scc(
    pkg_name: str,
    sle_sp_version: Literal[1, 2, 3, 4, 5] = 4,
    sle_version: Literal[12, 15] = 15,
) -> List[SccPackage]:
    """Fetch all packages which name matches ``pkg_name`` exactly from the SCC
    API.

    This function calls to the SCC API querying for the given package name for
    the product ``SLES/{sle_version}.{sle_sp_version}/x86_64``, filters out all
    packages whose name does not match ``pkg_name`` exactly and returns the
    result.

    """
    prod = f"SLES/{sle_version}.{sle_sp_version}/x86_64"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://scc.suse.com/api/package_search/packages?query={pkg_name}&product_id={prod}"
        ) as resp:
            pkgs = [SccPackage(**p) for p in (await resp.json())["data"]]

    exact_matches = []
    for p in pkgs:
        if p.name == pkg_name:
            exact_matches.append(p)

    if len(exact_matches) == 0:
        raise ValueError(f"No package found with the name {pkg_name} in {prod}")

    return exact_matches


def _pkg_compare(p1: SccPackage, p2: SccPackage) -> Literal[1, 0, -1]:
    return vercmp(p1.version, p2.version)


_pkg_cmp_key = cmp_to_key(_pkg_compare)


def get_latest_pkg_version(pkgs: List[SccPackage]) -> SccPackage:
    """Returns the latest version of a package according to rpm's version comparison
    rules from a list of packages.

    """
    return sorted(pkgs, key=_pkg_cmp_key, reverse=True)[0]


async def env_vars_from_scc_pkg_version(
    env_var_pkg_map: Dict[str, str],
    sp_version: SUPPORTED_SLE_SERVICE_PACKS = DEFAULT_SLE_SERVICE_PACK,
    sle_version: SUPPORTED_SLE_VERSIONS = DEFAULT_SLE_VERSION,
) -> Dict[str, str]:
    async def get_env_pkg_ver(env_var: str, pkg_name: str):
        return (
            env_var,
            get_latest_pkg_version(
                await get_pkgs_from_scc(pkg_name, sp_version, sle_version)
            ).version,
        )

    return dict(
        await asyncio.gather(*(get_env_pkg_ver(*v) for v in env_var_pkg_map.items()))
    )
