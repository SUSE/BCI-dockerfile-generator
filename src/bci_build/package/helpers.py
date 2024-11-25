from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import RELEASED_OS_VERSIONS
from bci_build.package import OsContainer
from bci_build.package import ParseVersion
from bci_build.package import _build_tag_prefix


def generate_package_version_check(
    pkg_name: str,
    pkg_version: str,
    parse_version: ParseVersion = ParseVersion.MINOR,
    use_target: bool = False,
) -> str:
    """Generate a RUN instruction for a :file:`Dockerfile` that will fail if the
    package with the name ``pkg_name`` is not at the provided version
    ``pkg_version``.

    The optional parameter ``parse_version`` allows you to
    restrict the version check to only match the major, major+minor, or
    major+minor+patch version.

    The optional parameter "use_target" generates a RUN instruction that checks
    for the ``pkg_name`` in the directory `/target` which is used in multi-stage
    builds.
    """
    cut_count = {
        ParseVersion.MAJOR: 1,
        ParseVersion.MINOR: 2,
        ParseVersion.PATCH: 3,
    }[parse_version]

    if pkg_version.count(".") != cut_count - 1:
        raise ValueError(
            f"Expected a version in the format {parse_version}, but got '{pkg_version}'"
        )

    return f"""# sanity check that the version from the tag is equal to the version of {pkg_name} that we expect
{DOCKERFILE_RUN} \\
    [ "$(rpm{' --root /target' if use_target else ''} -q --qf '%{{version}}' {pkg_name} | \\
    cut -d '.' -f -{cut_count})" = "{pkg_version}" ]"""


def generate_from_image_tag(os_version: OsVersion, container_name: str) -> str:
    repo = f"{_build_tag_prefix(os_version)}/{container_name}:{OsContainer.version_to_container_os_version(os_version)}"
    if not os_version.is_tumbleweed and os_version in RELEASED_OS_VERSIONS:
        return f"registry.suse.com/{repo}"
    return repo
