"""The PostgreSQL database container definitions."""

from pathlib import Path

from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import generate_disk_size_constraints

_POSTGRES_ENTRYPOINT = (
    Path(__file__).parent / "postgres" / "entrypoint.sh"
).read_bytes()
_POSTGRES_LICENSE = (Path(__file__).parent / "postgres" / "LICENSE").read_bytes()

# first list the SLE15 versions, then the TW specific versions
_POSTGRES_MAJOR_VERSIONS = [16, 15, 14] + [13, 12]
POSTGRES_CONTAINERS = [
    ApplicationStackContainer(
        name="postgres",
        package_name=f"postgres-{ver}-image",
        os_version=os_version,
        is_latest=ver == _POSTGRES_MAJOR_VERSIONS[0],
        pretty_name=f"PostgreSQL {ver}",
        support_level=SupportLevel.ACC,
        package_list=[f"postgresql{ver}-server", "findutils"],
        version=ver,
        additional_versions=["%%pg_version%%"],
        entrypoint=["/usr/local/bin/docker-entrypoint.sh"],
        cmd=["postgres"],
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": "%%pg_version%%",
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
                regex_in_build_description="%%pg_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        volumes=["$PGDATA"],
        exposes_tcp=[5432],
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
        [(15, variant) for variant in (OsVersion.SP5, OsVersion.TUMBLEWEED)]
        + [
            (16, variant)
            for variant in (OsVersion.SP6, OsVersion.SP7, OsVersion.TUMBLEWEED)
        ]
    )
    + [(pg_ver, OsVersion.TUMBLEWEED) for pg_ver in (14, 13, 12)]
]
