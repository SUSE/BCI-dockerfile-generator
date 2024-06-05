from bci_build.package import DOCKERFILE_RUN
from bci_build.package import PARSE_VERSION_T


def generate_package_version_check(
    pkg_name: str, pkg_version: str, parse_version: PARSE_VERSION_T = "minor"
) -> str:
    """Generate a RUN instruction for a :file:`Dockerfile` that will fail if the
    package with the name ``pkg_name`` is not at the provided version
    ``pkg_version``. The optional parameter ``parse_version`` allows you to
    restrict the version check to only match the major, major+minor, or
    major+minor+patch version.

    """
    cut_count: dict[PARSE_VERSION_T, int] = {"major": 1, "minor": 2, "patch": 3}

    return f"""# sanity check that the version from the tag is equal to the version of {pkg_name} that we expect
{DOCKERFILE_RUN} [ "$(rpm -q --qf '%{{version}}' {pkg_name} | cut -d '.' -f -{cut_count[parse_version]})" = "{pkg_version}" ]"""
