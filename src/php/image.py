"""Main module to generate the php container build descriptions

This is quite a hack to build a container that is more or less comparable to
<"upstream" https://github.com/docker-library/php/>_. We try to use the same
scripts as the upstream docker image uses but since we do not build php from
source in the container, we need to *somehow* provide the same sources as our
rpm packages do and replicate the build process entirely.

We approach this as follows:
- checkout the `php$VER` package from OBS
- set the ``BUILD_FLAVOR`` in the spec to the appropriate value
- build a container based on Leap 15.x into which we copy all patches, sources
  and gpg keys
- install rpmdevtools into the container
- use :command:`rpmspec -p` to parse the spec and extract the necessary
  information from it (e.g. how are patches applied)
"""
import asyncio
import hashlib
import os
import re
from dataclasses import dataclass
from dataclasses import field
from itertools import product
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

import aiofiles
import gnupg
from bci_build.logger import LOGGER
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from obs_package_update.util import RunCommand
from php.static import DOCKER_PHP_EXT_ENABLE
from php.templates import DOCKER_PHP_ENTRYPOINT
from php.templates import DOCKER_PHP_EXT_CONFIGURE
from php.templates import DOCKER_PHP_EXT_INSTALL
from php.templates import DOCKER_PHP_SOURCE
from php.templates import DOCKERFILE_END

# from php.static import SERVICE


run_cmd = RunCommand(logger=LOGGER)

_PHP_VERSION_RE = re.compile(r"php-(?P<version>(\d+\.?)+)\.tar\.xz$")

_PHP_FLAVOR_T = Literal["apache", "fpm", "cli"]
_ALL_PHP_FLAVORS: List[_PHP_FLAVOR_T] = ["apache", "fpm", "cli"]
_PHP_MAJOR_VERSION_T = Literal[7, 8]


@dataclass
class PhpPackage:
    version: str

    #: list of all patches extracted from the spec file
    #: the key is the patch number and the value the patch's file name
    patches: Dict[int, str] = field(default_factory=dict)

    cflags: str = ""
    cxxflags: str = ""
    ldflags: str = ""

    prep_section: str = ""

    php_url: str = ""
    php_asc_url: str = ""
    gpg_keys: List[str] = field(default_factory=list)
    archive_hash: str = ""

    _parsed_spec: str = ""


async def build_refreshed_bci_base(os_version: OsVersion) -> str:
    image_name = f"bci/bci-base-refreshed:15.{os_version}"
    async with aiofiles.tempfile.TemporaryDirectory() as tmp_dir:

        async def run(cmd: str):
            return await run_cmd(cmd, cwd=tmp_dir)

        container_name = (
            await run(f"buildah from registry.suse.com/bci/bci-base:15.{os_version}")
        ).stdout.strip()
        await run(f"buildah run {container_name} /bin/sh -c 'zypper -n ref'")
        await run(f"buildah commit {container_name} {image_name}")
    return image_name


async def build_php_devel_container(
    php_major_version: _PHP_MAJOR_VERSION_T,
    php_checkout_dest: str,
    os_version: OsVersion,
) -> PhpPackage:
    await run_cmd(
        f"osc co SUSE:SLE-15-SP{os_version}:Update/php{php_major_version} -o {php_checkout_dest}"
    )
    await run_cmd(
        f"sed -i 's/@BUILD_FLAVOR@%{{nil}}/%{{nil}}/' {php_checkout_dest}/php{php_major_version}.spec"
    )

    php_version: Optional[str] = None
    tarball_hash: Optional[str] = None
    gpg_keys: List[str] = []

    for file in os.listdir(php_checkout_dest):
        if match := _PHP_VERSION_RE.match(file):
            php_version = match.group("version")
            async with aiofiles.open(f"{php_checkout_dest}/{file}", "br") as tarball:
                sha_256 = hashlib.new("sha256")
                while True:
                    chunk = await tarball.read(2048)
                    if len(chunk) == 0:
                        break
                    sha_256.update(chunk)

                tarball_hash = sha_256.hexdigest()

        if file[-8:] == ".keyring":
            gpg = gnupg.GPG()
            gpg_keys = [
                key["fingerprint"]
                for key in gpg.scan_keys(f"{php_checkout_dest}/{file}")
            ]

    if not php_version:
        raise RuntimeError(
            "Could not infer php version from checked out php source code"
        )
    assert tarball_hash

    container = (
        await run_cmd(
            f"buildah from registry.opensuse.org/opensuse/leap-dnf:15.{os_version}"
        )
    ).stdout.strip()
    await run_cmd(
        f"buildah run {container} /bin/sh -c 'dnf -y install rpmdevtools && rpmdev-setuptree'"
    )
    await run_cmd(f"buildah config --workingdir /root/rpmbuild/SOURCES {container}")

    for file in (f"php{php_major_version}.spec", "macros.php"):
        await run_cmd(f"buildah copy {container} {php_checkout_dest}/{file}")

    # according to https://github.com/rpm-software-management/rpm/issues/2134,
    # we can get the list of patches of a spec via:
    #  rpmspec -q --srpm $fname.spec --qf "[%{PATCH}\n]"
    # Unfortunately this will just give us an array, but patches don't have to
    # be numbered sequentially...
    # So we have to extract the number from the spec file and save the patches
    # in a dictionary
    patches = (
        await run_cmd(
            f"buildah run {container} /bin/sh -c 'rpmspec -q --srpm php{php_major_version}.spec --qf"
            + r' "[%{PATCH}\n]"'
            + "'"
        )
    ).stdout.splitlines()

    ordered_patches = {}

    async def parse_spec():
        return (
            await run_cmd(
                f"buildah run {container} /bin/sh -c 'rpmspec -P php{php_major_version}.spec'"
            )
        ).stdout.strip()

    spec_file = await parse_spec()

    for patch in patches:
        regex = re.compile(
            r"^[P|p]atch(?P<patch_num>\d+):\s+" + re.escape(patch) + "$",
            flags=re.MULTILINE,
        )
        match = regex.search(spec_file)
        assert match

        ordered_patches[int(match.group("patch_num"))] = patch
        await run_cmd(f"buildah copy {container} {php_checkout_dest}/{patch}")

    # need to parse the spec file again, as the patches have just been copied there
    spec_file = await parse_spec()

    await run_cmd(f"buildah commit {container} php{php_major_version}-devel")
    return PhpPackage(
        version=php_version,
        patches=ordered_patches,
        archive_hash=tarball_hash,
        gpg_keys=gpg_keys,
        _parsed_spec=spec_file,
    )


async def extract_properties(
    php_major_version: _PHP_MAJOR_VERSION_T, tmpdir: str, os_version: OsVersion
) -> PhpPackage:
    php_package = await build_php_devel_container(php_major_version, tmpdir, os_version)

    flags = {"CFLAGS": "", "CXXFLAGS": "", "LDFLAGS": ""}
    for flag in flags:
        if not (
            matched_flags := re.search(
                rf"^(export )?{flag}=\"(?P<flags>.*)\"$",
                php_package._parsed_spec,
                re.MULTILINE,
            )
        ):
            raise ValueError(f"could not get {flag} from spec")
        flags[flag] = matched_flags.group("flags")

    php_package.cflags = flags["CFLAGS"]
    php_package.cxxflags = flags["CXXFLAGS"]
    php_package.ldflags = flags["LDFLAGS"]

    if not (
        asc_match := re.search(
            r"[S|s]ource\d+:\s+(?P<url>.*php-"
            + re.escape(f"{php_package.version}.tar.xz.asc")
            + ")$",
            php_package._parsed_spec,
            re.MULTILINE,
        )
    ):
        raise ValueError("Could not extract the url of the gpg key")
    php_package.php_asc_url = asc_match.group("url")

    if not (
        url_match := re.search(
            r"[S|s]ource\d+:\s+(?P<url>.*php-"
            + re.escape(f"{php_package.version}.tar.xz")
            + ")$",
            php_package._parsed_spec,
            re.MULTILINE,
        )
    ):
        raise ValueError("Could not extract the url of the tarball")
    php_package.php_url = url_match.group("url")

    prep_section = php_package._parsed_spec[
        php_package._parsed_spec.index("%prep")
        + len("%prep") : php_package._parsed_spec.index("%build")
    ]
    prep_section = re.sub(
        r"^%setup.*$",
        f'tar -xvf /usr/src/php-{ php_package.version }.tar.xz -C "$dir" && cd /usr/src/php/php-{ php_package.version }/',
        prep_section,
        flags=re.MULTILINE,
        count=1,
    )
    prep_section = re.sub("/root/rpmbuild/SOURCES/", "/usr/src/", prep_section)

    for match in re.finditer(
        r"^%patch(?P<patch_num>\d+)\s*(-p(?P<strip>\d+))?$", prep_section, re.MULTILINE
    ):
        patch_num = int(match.group("patch_num"))
        strip = int(match.group("strip") or 0)

        prep_section = re.sub(
            rf"^%patch{patch_num}\s*(\-p(?P<strip>\d+))?$",
            f"/usr/bin/cat /usr/src/{php_package.patches[patch_num]} | /usr/bin/patch -p{strip} --fuzz=0 --no-backup-if-mismatch",
            prep_section,
            flags=re.MULTILINE,
        )

    php_package.prep_section = prep_section

    return php_package


@dataclass
class PhpBCI(LanguageStackContainer):
    php_major_version: _PHP_MAJOR_VERSION_T = 8

    package_variant: _PHP_FLAVOR_T = "cli"

    @staticmethod
    def create_php_bci(
        os_version: OsVersion,
        php_major_version: _PHP_MAJOR_VERSION_T,
        package_variant: _PHP_FLAVOR_T,
    ) -> "PhpBCI":
        name = f"php-{php_major_version}-{package_variant}"
        return PhpBCI(
            name="php",
            pretty_name=f"PHP {php_major_version} {package_variant}",
            php_major_version=php_major_version,
            package_variant=package_variant,
            version=php_major_version,
            os_version=os_version,
            replacements_via_service=[
                Replacement("%%composer_version%%", package_name="php-composer2")
            ],
            package_name=f"{name}-image",
            _no_default_packages=True,
            _no_default_version=package_variant != "cli",
        )

    def __post_init__(self) -> None:
        super().__post_init__()
        self.custom_labelprefix_end = "php"

    async def late_init(self) -> None:
        self.extra_files: dict[str, str] = {
            "docker-php-ext-enable": DOCKER_PHP_EXT_ENABLE,
            # "_service": SERVICE,
        }

        async with aiofiles.tempfile.TemporaryDirectory() as tmpdir:
            tasks = []
            pkg = await extract_properties(
                self.php_major_version, tmpdir, self.os_version
            )
            for to_add in list(pkg.patches.values()) + ["README.macros"]:

                async def _read_file(fname: str) -> None:
                    async with aiofiles.open(f"{tmpdir}/{fname}") as to_read:
                        self.extra_files[fname] = await to_read.read(-1)

                tasks.append(_read_file(to_add))

            await asyncio.gather(*tasks)

        for template, fname in [
            (DOCKER_PHP_SOURCE, "docker-php-source"),
            (DOCKER_PHP_EXT_INSTALL, "docker-php-ext-install"),
            (DOCKER_PHP_EXT_CONFIGURE, "docker-php-ext-configure"),
            (DOCKER_PHP_ENTRYPOINT, "docker-php-entrypoint"),
        ]:
            self.extra_files[fname] = template.render(
                php_package=pkg, variant=self.package_variant
            )

        self.additional_versions = [
            f"{pkg.version}-{self.package_variant}",
            f"{self.php_major_version}-{self.package_variant}",
        ]
        if self.package_variant == "cli":
            self.additional_versions.extend(
                [
                    pkg.version,
                ]
            )

        self.custom_end = DOCKERFILE_END.render(
            php_major_version=self.php_major_version,
            php_package=pkg,
            variant=self.package_variant,
        )


PHP_IMAGES = [
    PhpBCI.create_php_bci(OsVersion.SP4, php_major_version, package_variant)
    for (php_major_version, package_variant) in product((8,), _ALL_PHP_FLAVORS)
]
