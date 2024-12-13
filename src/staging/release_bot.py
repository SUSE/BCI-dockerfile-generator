from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from enum import Enum
from enum import unique
from typing import Any
from typing import TypedDict

from ruamel.yaml.scalarstring import SingleQuotedScalarString

from bci_build.container_attributes import BuildType
from bci_build.package import ALL_CONTAINER_IMAGE_NAMES
from bci_build.package import ApplicationStackContainer
from bci_build.package import Arch
from bci_build.package import BaseContainerImage
from bci_build.package import DevelopmentContainer
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.registry import ApplicationCollectionRegistry


class CrbDefaults(TypedDict):
    arch: list[str]
    settings: dict[str, int | str]


class ContainerSettings(TypedDict):
    version: str
    flavor: str
    build: str
    groupid: int
    settings: dict[str, str]
    source: dict[str, str]
    testing: dict[str, str]
    release: dict[str, str]


class CrbYaml(TypedDict):
    defaults: CrbDefaults
    projects: dict[str, ContainerSettings]


class _CrbYamlDefaults(TypedDict):
    defaults: CrbDefaults


_DEFAULTS: _CrbYamlDefaults = {
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


_TEST_SETTINGS_KEYS = tuple(field.name for field in fields(TestSettings))


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
        OsVersion.SLE16_0: 608,
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
    def _recursive_to_str(d: dict[str, Any]) -> ContainerSettings:
        for k, v in d.items():
            if isinstance(v, str):
                d[k] = SingleQuotedScalarString(value=v)
            elif isinstance(v, dict):
                d[k] = ContainerTest._recursive_to_str(v)

        return d

    def to_dict(self) -> ContainerSettings:
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
    APPLICATION_COLLECTION = "app-collection"


def _generate_source_repository_name(container: BaseContainerImage) -> str:
    build_type = container.build_recipe_type or BuildType.DOCKER
    if (os_ver := container.os_version) == OsVersion.SLE16_0:
        return "containerfile" if build_type == BuildType.DOCKER else "images"

    assert os_ver.is_sle15
    return "containers" if build_type == BuildType.DOCKER else "images"


def _generate_test_repository_name(container: BaseContainerImage) -> str:
    if (os_ver := container.os_version).is_sle15:
        return "images"

    assert os_ver.is_slfo
    return _generate_source_repository_name(container)


def _source_test_release_prj_name(os_version: OsVersion) -> tuple[str, str, str]:
    """Returns a tuple of the source project name, test project name and release
    project name for the given os_version.

    """
    if os_version.is_sle15:
        return (
            (cr := f"SUSE:SLE-15-{os_version.pretty_print}:Update:CR"),
            f"{cr}:ToTest",
            f"SUSE:Containers:SLE-SERVER:15-{os_version.pretty_print}",
        )
    if os_version == OsVersion.SLE16_0:
        return (
            (cr := "SUSE:SLFO:Products:SLES:16.0"),
            f"{cr}:TEST",
            "SUSE:Containers:SLE-SERVER:16.0",
        )

    raise ValueError(f"Invalid {os_version=}")


def _container_openqa_name(container: BaseContainerImage) -> str:
    ctr_name = container.uid
    if suffix := getattr(container, "stability_tag", ""):
        ctr_name = f"{container.name}-{suffix}"

    if (os_ver := container.os_version).is_slfo:
        return f"SLE16-{ctr_name}"

    assert os_ver.is_sle15
    return f"SLE15-{os_ver.pretty_print}-{ctr_name}"


def generate_containers_test(family: OsVersion | ContainerFamily) -> CrbYaml:
    res: dict[str, ContainerSettings] = {}

    for ctr in list(ALL_CONTAINER_IMAGE_NAMES.values()):
        if (
            not ctr.os_version.is_sle15 and not ctr.os_version.is_slfo
        ) or ctr.os_version == OsVersion.SP7:
            continue

        if isinstance(family, OsVersion) and (
            family != ctr.os_version or not isinstance(ctr, OsContainer)
        ):
            continue

        if isinstance(family, ContainerFamily):
            # skip appcol unless explicitly wanted
            if (
                ctr.publish_registry == ApplicationCollectionRegistry()
                and family != ContainerFamily.APPLICATION_COLLECTION
            ):
                continue

            if family == ContainerFamily.APPLICATION and (
                not isinstance(ctr, ApplicationStackContainer)
                or ctr.publish_registry == ApplicationCollectionRegistry()
            ):
                continue

            if (
                family == ContainerFamily.APPLICATION_COLLECTION
                and ctr.publish_registry != ApplicationCollectionRegistry()
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
        name = _container_openqa_name(ctr)
        if name.endswith("3.9"):
            print(family, ctr.publish_registry)

        src_prj, test_prj, release_prj = _source_test_release_prj_name(ctr.os_version)

        source = TestPackage(
            project=src_prj,
            package=(pkg_name := ctr.package_name),
            repo=_generate_source_repository_name(ctr),
        )
        testing = TestPackage(
            project=test_prj,
            package=pkg_name,
            repo=(test_repo := _generate_test_repository_name(ctr)),
        )
        release = ReleasePackage(
            project=release_prj,
            package="",
            prefix=pkg_name,
            repo="containers",
        )

        if isinstance(ctr, OsContainer):
            build_tag = (
                ctr.build_tags[0].partition(":")[0]
                + ":"
                + OsContainer.version_to_container_os_version(ctr.os_version)
            )
        else:
            build_tag = f"{ctr.build_tags[0].partition(':')[0]}:{ctr.stability_tag or ctr.tag_version}"

        registry_path = f"registry.suse.de/{test_prj.lower().replace(':', '/')}/{test_repo}/{build_tag}"

        test_envs = TestSettings(
            BCI_TEST_ENVS=f"all,metadata,{ctr.test_environment}",
            BCI_IMAGE_MARKER=ctr.test_marker,
            BCI_IMAGE_NAME=ctr.test_marker,
            CONTAINER_IMAGE_TO_TEST=registry_path,
        )

        test = ContainerTest(
            version=f"15-{SP}" if ctr.os_version.is_sle15 else str(ctr.os_version),
            groupid=get_groupid(ctr),
            source=source,
            testing=testing,
            release=release,
            settings=test_envs,
            arch=ctr.exclusive_arch,
        )

        res[name] = test.to_dict()

    return {**_DEFAULTS, "projects": res}


def crb_config_merge(
    crb_yaml: CrbYaml,
    family: OsVersion | ContainerFamily,
    *,
    fatal_on_missing_ctr: bool = True,
) -> CrbYaml:
    generated_settings = generate_containers_test(family)

    for ctr_name in generated_settings["projects"].keys():
        settings = generated_settings["projects"][ctr_name]

        if ctr_name not in crb_yaml["projects"]:
            if fatal_on_missing_ctr:
                raise ValueError(
                    f"container {ctr_name} not in container-release-bot yaml"
                )
            else:
                continue

        crb_test_settings = crb_yaml["projects"][ctr_name]["settings"]

        for k, v in crb_test_settings.items():
            if k not in _TEST_SETTINGS_KEYS:
                settings["settings"][k] = (
                    SingleQuotedScalarString(v) if isinstance(v, str) else v
                )

    projects_with_crb_order = {
        k: generated_settings["projects"][k]
        for k in crb_yaml["projects"].keys()
        if k in generated_settings["projects"]
    }
    generated_settings["projects"] = projects_with_crb_order

    return generated_settings


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
                OsVersion.SLE16_0,
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

    yaml_l = YAML()
    with open((yaml_path := os.path.expanduser(args.destination[0]))) as crb_yaml_f:
        existing_settings = yaml_l.load(crb_yaml_f)

    yaml = YAML(typ="rt", output=open(yaml_path, "w"))
    yaml.preserve_quotes = False
    yaml.indent(mapping=2, sequence=4, offset=2)

    with yaml:
        yaml.dump(
            crb_config_merge(existing_settings, family, fatal_on_missing_ctr=False)
        )
