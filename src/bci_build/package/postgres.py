"""The PostgreSQL database container definitions."""

from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag

_POSTGRES_ENTRYPOINT = (
    Path(__file__).parent / "postgres" / "entrypoint.sh"
).read_bytes()
_POSTGRES_LICENSE = (Path(__file__).parent / "postgres" / "LICENSE").read_bytes()

# first list the SLE15 versions, then the TW specific versions
_POSTGRES_MAJOR_VERSIONS = [17, 16, 15, 14] + [13]
POSTGRES_CONTAINERS = [
    ApplicationStackContainer(
        name="postgres",
        package_name=f"postgres-{ver}-image",
        os_version=os_version,
        is_latest=ver == _POSTGRES_MAJOR_VERSIONS[0],
        pretty_name=f"PostgreSQL {ver}",
        support_level=SupportLevel.ACC,
        supported_until=(
            _SUPPORTED_UNTIL_SLE[os_version]
            if os_version in (OsVersion.SP5, OsVersion.SP6)
            else None
        ),
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        package_list=[
            "libpq5",
            f"postgresql{ver}-server",
            "findutils",
            "coreutils",
            "sed",
            "util-linux",  # for setpriv :-(
        ]
        + (
            [
                f"postgresql{ver}-pgvector",
            ]
            if os_version.is_tumbleweed
            else []
        ),
        version="%%pg_patch_version%%",
        tag_version=str(ver),
        _min_release_counter=70 if ver == 16 else None,
        additional_versions=["%%pg_minor_version%%"],
        entrypoint=["/usr/local/bin/docker-entrypoint.sh"],
        cmd=["postgres"],
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": "%%pg_minor_version%%",
            "PGDATA": "/var/lib/pgsql/data",
        },
        license="PostgreSQL",
        extra_files={
            "docker-entrypoint.sh": _POSTGRES_ENTRYPOINT,
            "LICENSE": _POSTGRES_LICENSE,
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(8),
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%pg_minor_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version=ParseVersion.MINOR,
            ),
            Replacement(
                regex_in_build_description="%%pg_patch_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version=ParseVersion.PATCH,
            ),
        ],
        volumes=["$PGDATA"],
        exposes_ports=[TCP(5432)],
        custom_end=rf"""COPY docker-entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/docker-entrypoint.sh; \
    sed -i -e 's/exec gosu postgres "/exec setpriv --reuid=postgres --regid=postgres --clear-groups -- "/g' /usr/local/bin/docker-entrypoint.sh; \
    mkdir /docker-entrypoint-initdb.d; \
    install -m 1775 -o postgres -g postgres -d /run/postgresql; \
    install -d -m 0700 -o postgres -g postgres $PGDATA; \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql{ver}/postgresql.conf.sample

STOPSIGNAL SIGINT
HEALTHCHECK --interval=10s --start-period=10s --timeout=5s \
    CMD pg_isready -U ${{POSTGRES_USER:-postgres}} -h localhost -p 5432
""",
    )
    for ver, os_version in (
        [(15, variant) for variant in (OsVersion.TUMBLEWEED,)]
        + [
            (16, variant)
            for variant in (OsVersion.SP7, OsVersion.SL16_0, OsVersion.TUMBLEWEED)
        ]
        + [
            (17, variant)
            for variant in (OsVersion.SP7, OsVersion.SL16_0, OsVersion.TUMBLEWEED)
        ]
    )
    + [(pg_ver, OsVersion.TUMBLEWEED) for pg_ver in (14, 13)]
]
