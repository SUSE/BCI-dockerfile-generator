from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import unique
from typing import Any

from ruamel.yaml.scalarstring import SingleQuotedScalarString

from bci_build.package import ALL_CONTAINER_IMAGE_NAMES
from bci_build.package import ApplicationStackContainer
from bci_build.package import Arch
from bci_build.package import BaseContainerImage
from bci_build.package import DevelopmentContainer
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from dotnet.updater import DOTNET_IMAGES

_DEFAULTS = {
    "defaults": {
        "arch": ["aarch64", "x86_64", "s390x", "ppc64le"],
        "settings": {
            "RETRY": 1,
            "BCI_TEST_ENVS": SingleQuotedScalarString("all,metadata"),
        },
    }
}


@dataclass(frozen=True)
class TestSettings:
    BCI_TEST_ENVS: str = ""
    BCI_IMAGE_MARKER: str = ""
    BCI_IMAGE_NAME: str = ""
    CONTAINER_IMAGE_TO_TEST: str = ""


@dataclass(frozen=True)
class TestPackage:
    project: str = ""
    repo: str = ""
    package: str = ""


@dataclass(frozen=True)
class ReleasePackage(TestPackage):
    prefix: str = ""


def get_groupid(ctr: BaseContainerImage) -> int:
    if isinstance(ctr, ApplicationStackContainer):
        return 445
    if isinstance(ctr, DevelopmentContainer):
        return 444

    return {
        OsVersion.SP3: 442,
        OsVersion.SP4: 443,
        OsVersion.SP5: 475,
        OsVersion.SP6: 538,
    }[ctr.os_version]


@dataclass(frozen=True)
class ContainerTest:
    version: str
    flavor: str = "BCI-Updates"
    build: str = "%build_%sourcepackage"
    groupid: int = 0

    arch: list[Arch] | None = None

    settings: TestSettings = field(default_factory=TestSettings)
    source: TestPackage = field(default_factory=TestPackage)
    testing: TestPackage = field(default_factory=TestPackage)
    release: ReleasePackage = field(default_factory=ReleasePackage)

    @staticmethod
    def _recursive_to_str(d: dict[str, Any]) -> dict[str, Any]:
        for k, v in d.items():
            if isinstance(v, str):
                d[k] = SingleQuotedScalarString(value=v)
            elif isinstance(v, dict):
                d[k] = ContainerTest._recursive_to_str(v)

        return d

    def to_dict(self) -> dict[str, Any]:
        res = {}
        for k, v in self.__dict__.items():
            if not v:
                continue

            if k == "arch":
                assert self.arch is not None
                # omit exclusive arch when it's all architectures
                if len(self.arch) != 4:
                    res[k] = [str(arch) for arch in self.arch]

            else:
                if hasattr(v, "__dict__"):
                    res[k] = v.__dict__
                else:
                    res[k] = v
        return ContainerTest._recursive_to_str(res)


@unique
class ContainerFamily(Enum):
    APPLICATION = "app"
    LANGUAGE = "lang"


def generate_containers_test(family: OsVersion | ContainerFamily) -> dict[str, Any]:
    res = {}

    for ctr in list(ALL_CONTAINER_IMAGE_NAMES.values()) + DOTNET_IMAGES:
        if not ctr.os_version.is_sle15:
            continue

        if isinstance(family, OsVersion) and (
            family != ctr.os_version or not isinstance(ctr, OsContainer)
        ):
            continue

        if isinstance(family, ContainerFamily):
            if family == ContainerFamily.APPLICATION and not isinstance(
                ctr, ApplicationStackContainer
            ):
                continue

            # skip everything that is not a devcontainer but that is an
            # appcontainer (appcontainers are subclases of devcontainers)
            if family == ContainerFamily.LANGUAGE:
                if isinstance(ctr, ApplicationStackContainer):
                    continue
                if not isinstance(ctr, DevelopmentContainer):
                    continue

        SP = ctr.os_version.pretty_print
        name = f"SLE15-{SP}-{ctr.uid}"

        source = TestPackage(
            project=(cr := f"SUSE:SLE-15-{SP}:Update:CR"),
            package=ctr.package_name,
            repo=ctr.build_recipe_type.repository_name,
        )
        testing = TestPackage(
            project=f"{cr}:ToTest", package=ctr.package_name, repo="images"
        )
        release = ReleasePackage(
            project=f"SUSE:Containers:SLE-SERVER:15-{SP}",
            package="",
            prefix=ctr.package_name,
            repo="containers",
        )

        registry_path = f"registry.suse.de/suse/sle-15-{SP.lower()}/update/cr/totest/images/{ctr.build_tags[0]}"
        if registry_path.endswith("%OS_VERSION_ID_SP%"):
            registry_path = registry_path.replace(
                "%OS_VERSION_ID_SP%",
                OsContainer.version_to_container_os_version(ctr.os_version),
            )
        test_envs = TestSettings(
            BCI_TEST_ENVS=f"all,metadata,{ctr.test_environment}",
            BCI_IMAGE_MARKER=ctr.test_marker,
            BCI_IMAGE_NAME=ctr.test_marker,
            CONTAINER_IMAGE_TO_TEST=registry_path,
        )

        test = ContainerTest(
            version=f"15-{SP}",
            groupid=get_groupid(ctr),
            source=source,
            testing=testing,
            release=release,
            settings=test_envs,
            arch=ctr.exclusive_arch,
        )

        res[name] = test.to_dict()

    return {**_DEFAULTS, "projects": res}


def dump_data() -> None:
    import argparse
    import os.path

    from ruamel.yaml import YAML

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ctr-family",
        "-f",
        nargs=1,
        required=True,
        choices=[
            str(v.value)
            for v in (
                ContainerFamily.APPLICATION,
                ContainerFamily.LANGUAGE,
                OsVersion.SP3,
                OsVersion.SP4,
                OsVersion.SP5,
                OsVersion.SP6,
            )
        ],
    )
    parser.add_argument(
        "--destination",
        "-d",
        nargs=1,
        required=True,
        type=str,
        help="File to which the yaml will be written",
    )

    args = parser.parse_args()

    try:
        family = OsVersion.parse(args.ctr_family[0])
    except ValueError:
        family = ContainerFamily(args.ctr_family[0])

    yaml = YAML(typ="rt", output=open(os.path.expanduser(args.destination[0]), "w"))
    yaml.preserve_quotes = False
    yaml.map_indent = 2
    yaml.sequence_indent = 2

    with yaml:
        yaml.dump(generate_containers_test(family))
