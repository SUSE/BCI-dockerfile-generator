from enum import Enum
from enum import auto
from enum import unique

import jinja2

from bci_build.os_version import OsVersion

USERS_FOR_PRODUCTION = [
    "avicenzi",
    "dirkmueller",
    "pushman",
]

USERS_FOR_STAGING = ["avicenzi"]

META_TEMPLATE = jinja2.Environment(autoescape=True).from_string("""<project name="{{ project_name }}">
  <title>{{ project_title }}</title>
{% if project_description %}  <description>{{ project_description }}</description>{% else %}  <description/>{% endif %}
{% for user in maintainers %}  <person userid="{{ user }}" role="maintainer"/>
{% endfor %}{% if extra_header %}
{{ extra_header | safe }}{% endif %}
  <build>
    <enable/>
  </build>
  <publish>
    <enable/>
  </publish>
  <debuginfo>
    <enable/>
  </debuginfo>
  <repository name="standard">
{% for prj, repo in repository_paths %}    <path project="{{ prj }}" repository="{{ repo }}"/>
{% endfor %}    <arch>x86_64</arch>
    <arch>aarch64</arch>
{%- if with_all_arches %}
    <arch>s390x</arch>
    <arch>ppc64le</arch>
{%- endif %}
  </repository>
{%- if with_product_repo %}
  <repository name="containerkiwi">
{%- else %}
  <repository name="images">
{%- endif %}
{%- if not with_released_containers %}
    <path project="{{ project_name }}" repository="containerfile"/>
{%- endif %}
    <path project="{{ project_name }}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
{%- if with_all_arches %}
    <arch>s390x</arch>
    <arch>ppc64le</arch>
{%- endif %}
  </repository>{% if with_product_repo %}
  <repository name="product">
    <path project="{{ project_name }}" repository="containerfile"/>
{%- if with_product_repo %}
    <path project="{{ project_name }}" repository="containerkiwi"/>
{%- else %}
    <path project="{{ project_name }}" repository="images"/>
{%- endif %}
    <path project="{{ project_name }}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
{%- if with_all_arches %}
    <arch>s390x</arch>
    <arch>ppc64le</arch>
{%- endif %}
  </repository>{% endif %}{% if with_helmcharts_repo %}
  <repository name="helmcharts">
    <path project="{{ project_name }}" repository="standard"/>
    <arch>x86_64</arch>
  </repository>{% endif %}
  <repository name="containerfile">
{%- if not with_released_containers %}
{%- if with_product_repo %}
    <path project="{{ project_name }}" repository="containerkiwi"/>
{%- else %}
    <path project="{{ project_name }}" repository="images"/>
{%- endif %}
{%- endif %}
    <path project="{{ project_name }}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
{%- if with_all_arches %}
    <arch>s390x</arch>
    <arch>ppc64le</arch>
{%- endif %}
  </repository>
</project>
""")


@unique
class ProjectType(Enum):
    DEVEL = auto()
    CR = auto()
    STAGING = auto()


def generate_project_name(
    os_version: OsVersion,
    project_type: ProjectType,
    osc_username: str,
    branch_name: str | None = None,
) -> str:
    res = {
        ProjectType.DEVEL: "devel:BCI:",
        ProjectType.CR: f"home:{osc_username}:BCI:CR:",
        ProjectType.STAGING: f"home:{osc_username}:BCI:Staging:",
    }[project_type]

    if os_version.is_sle15:
        res += f"SLE-15-SP{str(os_version)}"
    else:
        res += str(os_version)

    if project_type == ProjectType.STAGING:
        if not branch_name:
            raise ValueError("staging projects need a branch name")
        res += ":" + branch_name

    return res


def generate_meta(
    os_version: OsVersion,
    project_type: ProjectType,
    osc_username: str,
    branch_name: None | str = None,
) -> tuple[str, str]:
    prj_name = generate_project_name(
        os_version, project_type, osc_username, branch_name
    )

    if project_type == ProjectType.DEVEL:
        users = USERS_FOR_PRODUCTION
    else:
        users = USERS_FOR_STAGING + [osc_username]

    with_all_arches = (os_version != OsVersion.TUMBLEWEED) or (
        project_type in (ProjectType.CR, ProjectType.DEVEL)
    )
    with_helmcharts_repo = project_type == ProjectType.DEVEL and not os_version.is_sl16
    with_released_containers = (
        project_type == ProjectType.DEVEL and not os_version.is_sl16
    )

    repository_paths: tuple[tuple[str, str], ...]
    if os_version.is_sle15 or os_version.is_sl16:
        if os_version.is_sle15:
            first_prj = "SUSE:Registry"
            last_prj = f"SUSE:SLE-15-SP{str(os_version)}:Update"
        else:
            assert os_version.is_sl16
            first_prj = "SUSE:SLFO:Products:SLES:16.0"
            last_prj = "SUSE:SLFO:Main:Build"
            if os_version == OsVersion.SL16_0:
                first_prj = "SUSE:Registry"
                last_prj = "SUSE:SLFO:Products:SLES:16.0"

        repository_paths: tuple[tuple[str, str], ...] = ((first_prj, "standard"),)
        if (os_version.is_sl16 or os_version.is_sle15) and (
            project_type == ProjectType.STAGING
        ):
            repository_paths += (
                (
                    devel_prj := generate_project_name(
                        os_version, ProjectType.DEVEL, ""
                    ),
                    "containerfile",
                ),
                (devel_prj, "containerkiwi" if os_version.is_sl16 else "images"),
                (devel_prj, "standard"),
            )
        repository_paths += ((last_prj, "standard"),)
    else:
        assert os_version.is_tumbleweed
        repository_paths = (
            ("openSUSE:Factory", "containerfile"),
            ("openSUSE:Factory", "images"),
            ("openSUSE:Factory:ARM", "containerfile"),
            ("openSUSE:Factory:ARM", "images"),
            ("openSUSE:Factory:ARM", "standard"),
            ("openSUSE:Factory:PowerPC", "standard"),
            ("openSUSE:Factory:zSystems", "standard"),
            ("openSUSE:Factory", "snapshot"),
        )

    if project_type == ProjectType.STAGING:
        assert branch_name
        description = f"Staging project for https://github.com/SUSE/BCI-dockerfile-generator/tree/{branch_name}"
        title = "Staging project"
    else:
        description = {
            ProjectType.DEVEL: "Development",
            ProjectType.CR: "Continuous Rebuild",
        }[project_type] + " project"
        title = description

    description += f" for {os_version.full_os_name}"
    title += f" for {os_version.full_os_name}"

    if project_type == ProjectType.DEVEL:
        description = (
            "BCI "
            + description
            + "\nThis project is automatically updated from git. Please do **not** send submit requests, create an issue in the [bci-dockerfile-generator](https://github.com/SUSE/bci-dockerfile-generator) repository instead"
        )
        title = "BCI " + title

    extra_header = None
    if project_type == ProjectType.CR:
        extra_header = f"  <scmsync>https://github.com/SUSE/bci-dockerfile-generator#{os_version.deployment_branch_name}</scmsync>"
    if project_type == ProjectType.DEVEL and os_version == OsVersion.TUMBLEWEED:
        # need to add factory-maintainers group as a maintainer so that the bot
        # can accept SRs
        extra_header = """  <group groupid="factory-maintainers" role="maintainer"/>"""

    return prj_name, META_TEMPLATE.render(
        project_title=title,
        project_description=description,
        project_name=prj_name,
        maintainers=users,
        with_all_arches=with_all_arches,
        with_released_containers=with_released_containers,
        with_helmcharts_repo=with_helmcharts_repo,
        with_product_repo=os_version.is_sl16,
        repository_paths=repository_paths,
        description=description,
        extra_header=extra_header,
    )
