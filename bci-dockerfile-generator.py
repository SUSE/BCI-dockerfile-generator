#!/usr/bin/env python3

import abc
import os
import glob
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

import jinja2


with open(
    os.path.join(os.path.dirname(__file__), "Dockerfile.j2"), "r"
) as dockerfile_tmpl:
    DOCKERFILE_TEMPLATE = jinja2.Template(dockerfile_tmpl.read(-1))

with open(os.path.join(os.path.dirname(__file__), "_service"), "r") as service:
    _SERVICE = service.read(-1)


@dataclass(frozen=True)
class EnvironmentVariable:
    name: str
    value: str

    def __str__(self) -> str:
        return f"{self.name}={self.value}"


@dataclass
class BaseContainerImage(abc.ABC):
    name: str

    #: Human readable name that will be inserted into the image title and description
    pretty_name: str

    #: The container from which this one is derived. defaults to
    #: ``suse/sle15:15.$SP``
    from_image: Optional[str] = None

    #: an optional entrypoint for the image, is omitted if empty or ``None``
    entrypoint: Optional[str] = None

    #: Extra environment variables to be set in the container
    env: Union[Dict[str, Union[str, int]], Dict[str, str], Dict[str, int]] = field(
        default_factory=dict
    )

    #: additional labels that should be added to the image
    extra_labels: Dict[str, str] = field(default_factory=dict)

    #: Packages to be installed inside the container
    package_list: List[str] = field(default_factory=list)

    custom_end: str = ""

    #: the maintainer of this image, defaults to SUSE
    maintainer: str = "SUSE LLC (https://www.suse.com/)"

    #: additional files that belong into this container-package
    #: the key is the filename, the value are the file contents
    extra_files: Dict[str, Union[str, bytes]] = field(default_factory=dict)

    #: by default the containers get the labelprefix
    #: ``com.suse.bci.{self.name}``. If this value is not an empty string, then
    #: it is used instead of the name after ``com.suse.bci.``.
    custom_labelprefix_end: str = ""

    def __post_init__(self) -> None:
        if not self.package_list:
            raise ValueError(f"No packages were added to {self.pretty_name}.")

    @property
    @abc.abstractmethod
    def nvr(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def version_label(self) -> str:
        pass

    @property
    def packages(self) -> str:
        return " ".join(self.package_list)

    @property
    def env_lines(self) -> str:
        return "\n".join(f'ENV {k}="{v}"' for k, v in self.env.items())

    @property
    @abc.abstractmethod
    def build_tags(self) -> List[str]:
        pass

    @property
    @abc.abstractmethod
    def reference(self) -> str:
        pass

    @property
    def description(self) -> str:
        return f"Image containing {self.pretty_name} based on the SLE Base Container Image."

    @property
    def title(self) -> str:
        return f"SLE BCI {self.pretty_name} container"

    @property
    def extra_label_lines(self) -> str:
        return "\n".join(f'LABEL {k}="{v}"' for k, v in self.extra_labels.items())

    @property
    def labelprefix(self) -> str:
        return f"com.suse.bci.{self.custom_labelprefix_end or self.name}"


@dataclass
class LanguageStackContainer(BaseContainerImage):
    #: the primary version of the language or application inside this container
    version: Union[str, int] = ""

    #: indicates whether this is the latest version of this language or
    #: application stack
    latest: bool = True

    #: additional versions that should be added as tags to this container
    #: (e.g. ``latest``)
    additional_versions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("A language stack container requires a version")

    @property
    def version_label(self) -> str:
        return str(self.version)

    @property
    def nvr(self) -> str:
        return f"{self.name}-{self.version}"

    @property
    def build_tags(self) -> List[str]:
        return (
            [f"bci/{self.name}:{self.version_label}"]
            + ([f"bci/{self.name}:latest"] if self.latest else [])
            + [f"bci/{self.name}:{self.version_label}-%RELEASE%"]
            + [f"bci/{self.name}:{ver}" for ver in self.additional_versions]
        )

    @property
    def reference(self) -> str:
        return f"registry.suse.com/{self.build_tags[0]}"


@dataclass
class OsContainer(BaseContainerImage):
    @property
    def nvr(self) -> str:
        return self.name

    @property
    def version_label(self) -> str:
        return "%OS_VERSION_ID_SP%.%RELEASE%"

    @property
    def build_tags(self) -> List[str]:
        return [
            f"bci/{self.name}:{self.version_label}",
            f"bci/{self.name}:%OS_VERSION_ID_SP%",
        ]

    @property
    def reference(self) -> str:
        return f"registry.suse.com/{self.build_tags[1]}"


PYTHON_3_6 = LanguageStackContainer(
    name="python",
    pretty_name="Python",
    version="3.6",
    latest=False,
    env={
        "PYTHON_VERSION": "3.6.13",
        "PIP_VERSION": "20.0.2",
    },
    package_list=[
        "python3",
        "python3-pip",
        "python3-wheel",
        "curl",
        "git-core",
    ],
)

PYTHON_3_9 = LanguageStackContainer(
    name="python",
    pretty_name="Python 3.9",
    version="3.9",
    additional_versions=["3"],
    env={"PYTHON_VERSION": "3.9.6", "PIP_VERSION": "20.0.4"},
    package_list=[
        "python39",
        "python39-pip",
        "curl",
        "git-core",
    ],
    custom_end=r"""RUN rpm -e --nodeps $(rpm -qa|grep libpython3_6) python3-base && \
    ln -s /usr/bin/python3.9 /usr/bin/python3 && \
    ln -s /usr/bin/pip3.9 /usr/bin/pip3 && \
    ln -s /usr/bin/pip3.9 /usr/bin/pip""",
)

RUBY_2_5 = LanguageStackContainer(
    name="ruby",
    pretty_name="Ruby 2.5",
    version="2.5",
    additional_versions=["2"],
    env={
        "RUBY_VERSION": "2.5.9",
        "GEM_VERSION": "2.7.6.3",
        "BUNDLER_VERSION": "1.16.1",
    },
    package_list=[
        "ruby2.5",
        "ruby2.5-rubygem-bundler",
        "ruby2.5-devel",
        "curl",
        "git-core",
        "distribution-release",
        # additional dependencies to build rails, ffi, sqlite3 gems -->
        "gcc-c++",
        "sqlite3-devel",
        "make",
        "awk",
        # additional dependencies supplementing rails
        "timezone",
    ],
    # as we only ship one ruby version, we want to make sure that binaries belonging
    # to our gems get installed as `bin` and not as `bin.ruby2.5`
    custom_end="RUN sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc",
)

(GOLANG_1_16, GOLANG_1_17) = (
    LanguageStackContainer(
        name="golang",
        pretty_name=f"Golang {ver}",
        version=ver,
        latest=ver == "1.17",
        env={
            "GOLANG_VERSION": ver,
            "PATH": "/go/bin:/usr/local/go/bin:/root/go/bin/:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        },
        package_list=[f"go{ver}", "distribution-release", "make"],
        extra_files={
            # the go binaries are huge and will ftbfs on workers with a root partition with 4GB
            "_constraints": """<constraints>
  <hardware>
    <disk>
      <size unit="G">6</size>
    </disk>
  </hardware>
</constraints>
"""
        },
    )
    for ver in ("1.16", "1.17")
)

NODE_VERSIONS = [12, 14]
(NODEJS_12, NODEJS_14) = (
    LanguageStackContainer(
        name="nodejs",
        version=str(ver),
        pretty_name=f"Node.js {ver}",
        latest=ver == max(NODE_VERSIONS),
        package_list=[
            f"nodejs{ver}",
            # devel dependencies:
            f"npm{ver}",
            "git-core",
            # dependency of nodejs:
            "update-alternatives",
            "distribution-release",
        ],
        env={
            "NODE_VERSION": ver,
            "NPM_VERSION": "6.14.14",
        },
    )
    for ver in NODE_VERSIONS
)

JAVA_ENV = {
    "JAVA_BINDIR": "/usr/lib64/jvm/java/bin",
    "JAVA_HOME": "/usr/lib64/jvm/java",
    "JAVA_ROOT": "/usr/lib64/jvm/java",
    "JAVA_VERSION": "11",
}
OPENJDK_11 = LanguageStackContainer(
    name="openjdk",
    pretty_name="OpenJDK 11",
    version="11",
    package_list=["java-11-openjdk"],
    env=JAVA_ENV,
)
OPENJDK_11_DEVEL = LanguageStackContainer(
    name="openjdk-devel",
    custom_labelprefix_end="openjdk.devel",
    pretty_name="OpenJDK 11 development",
    version="11",
    package_list=["java-11-openjdk-devel", "git-core", "maven"],
    entrypoint="jshell",
    from_image="bci/openjdk:11",
    env=JAVA_ENV,
)

INIT = OsContainer(
    name="init",
    pretty_name="Systemd",
    package_list=["systemd"],
    extra_labels={
        "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
    },
)

# rmt-nginx
NGINX_FILES = {}
for filename in [
    "docker-entrypoint.sh",
    "LICENSE",
    "10-listen-on-ipv6-by-default.sh",
    "20-envsubst-on-templates.sh",
    "30-tune-worker-processes.sh",
    "index.html",
]:
    with open(os.path.join(os.path.dirname(__file__), "nginx", filename)) as cursor:
        NGINX_FILES[filename] = cursor.read(-1)


NGINX = LanguageStackContainer(
    name="rmt-nginx",
    pretty_name="rmt-nginx",
    version="1.19",
    package_list=["nginx", "distribution-release"],
    entrypoint='["/docker-entrypoint.sh"]',
    extra_files=NGINX_FILES,
    custom_end="""
RUN mkdir /docker-entrypoint.d
COPY 10-listen-on-ipv6-by-default.sh /docker-entrypoint.d/
COPY 20-envsubst-on-templates.sh /docker-entrypoint.d/
COPY 30-tune-worker-processes.sh /docker-entrypoint.d/
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
RUN chmod +x /docker-entrypoint.d/20-envsubst-on-templates.sh
RUN chmod +x /docker-entrypoint.d/30-tune-worker-processes.sh
RUN chmod +x /docker-entrypoint.sh

COPY index.html /srv/www/htdocs/

RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

EXPOSE 80

STOPSIGNAL SIGQUIT

CMD ["nginx", "-g", "daemon off;"]
""",
)

with open(
    os.path.join(os.path.dirname(__file__), "postgres-entrypoint.sh")
) as entrypoint:
    POSTGRES_ENTRYPOINT = entrypoint.read(-1)

with open(os.path.join(os.path.dirname(__file__), "postgres-LICENSE")) as license_file:
    POSTGRES_LICENSE = license_file.read(-1)


POSTGRES_MAJOR_VERSIONS = [14, 13, 12, 10]
POSTGRES_MINOR_VERSIONS = [1, 5, 9, 19]
POSTGRES_VERSIONS = list(zip(POSTGRES_MAJOR_VERSIONS, POSTGRES_MINOR_VERSIONS))
POSTGRES_14, POSTGRES_13, POSTGRES_12, POSTGRES_10 = (
    LanguageStackContainer(
        name="postgres",
        pretty_name=f"PostgreSQL {ver}",
        package_list=[f"postgresql{ver}-server", "distribution-release"],
        version=ver,
        additional_versions=[f"{ver}.{minor_ver}"],
        latest=ver == max(POSTGRES_MAJOR_VERSIONS),
        entrypoint='["docker-entrypoint.sh"]',
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": f"{ver}.{minor_ver}",
            "PGDATA": "/var/lib/postgresql/data",
        },
        extra_files={
            "docker-entrypoint.sh": POSTGRES_ENTRYPOINT,
            "LICENSE": POSTGRES_LICENSE,
        },
        custom_end=rf"""
VOLUME /var/lib/postgresql/data

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    ln -s su /usr/bin/gosu && \
    mkdir /docker-entrypoint-initdb.d && \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql{ver}/postgresql.conf.sample

STOPSIGNAL SIGINT
EXPOSE 5432
CMD ["postgres"]
""",
    )
    for (ver, minor_ver) in POSTGRES_VERSIONS
)


with open(
    os.path.join(os.path.dirname(__file__), "mariadb-entrypoint.sh")
) as entrypoint:
    MARIADB = LanguageStackContainer(
        name="mariadb",
        maintainer="bruno.leon@suse.de",
        version="10.6",
        pretty_name="MariaDB server",
        package_list=["mariadb", "mariadb-tools", "gawk", "timezone", "util-linux"],
        entrypoint='["docker-entrypoint.sh"]',
        extra_files={"docker-entrypoint.sh": entrypoint.read(-1)},
        custom_end=r"""RUN mkdir /docker-entrypoint-initdb.d

VOLUME /var/lib/mysql

# docker-entrypoint from https://github.com/MariaDB/mariadb-docker.git
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
RUN ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat

RUN sed -i 's#gosu mysql#su mysql -s /bin/bash -m#g' /usr/local/bin/docker-entrypoint.sh

# Ensure all logs goes to stdout
RUN sed -i 's/^log/#log/g' /etc/my.cnf

# Disable binding to localhost only, doesn't make sense in a container
RUN sed -i -e 's|^\(bind-address.*\)|#\1|g' /etc/my.cnf

RUN mkdir /run/mysql

EXPOSE 3306
CMD ["mariadbd"]
""",
    )

with open(os.path.join(os.path.dirname(__file__), "rmt-entrypoint.sh")) as entrypoint:
    RMT_CONTAINER = LanguageStackContainer(
        name="rmt-server",
        maintainer="bruno.leon@suse.de",
        pretty_name="RMT Server",
        version="2.7",
        package_list=["rmt-server", "catatonit"],
        entrypoint="/usr/local/bin/entrypoint.sh",
        env={"RAILS_ENV": "production", "LANG": "en"},
        extra_files={"entrypoint.sh": entrypoint.read(-1)},
        custom_end="""COPY entrypoint.sh /usr/local/bin/entrypoint.sh
CMD ["/usr/share/rmt/bin/rails", "server", "-e", "production"]
""",
    )


THREE_EIGHT_NINE_DS = LanguageStackContainer(
    name="389-ds",
    maintainer="wbrown@suse.de",
    pretty_name="389 directory server",
    package_list=["389-ds", "timezone", "openssl"],
    version="1.4",
    custom_end=r"""EXPOSE 3389 3636

RUN mkdir -p /data/config && \
    mkdir -p /data/ssca && \
    mkdir -p /data/run && \
    mkdir -p /var/run/dirsrv && \
    ln -s /data/config /etc/dirsrv/slapd-localhost && \
    ln -s /data/ssca /etc/dirsrv/ssca && \
    ln -s /data/run /var/run/dirsrv

VOLUME /data

HEALTHCHECK --start-period=5m --timeout=5s --interval=5s --retries=2 \
    CMD /usr/lib/dirsrv/dscontainer -H

CMD [ "/usr/lib/dirsrv/dscontainer", "-r" ]
""",
)

PHP_VERSIONS = [7, 8]
(PHP_7, PHP_8) = (
    LanguageStackContainer(
        name="php",
        pretty_name=f"PHP {ver}",
        package_list=[
            f"php{ver}",
            f"php{ver}-composer",
            f"php{ver}-zip",
            f"php{ver}-zlib",
            f"php{ver}-phar",
            f"php{ver}-mbstring",
            "curl",
            "git-core",
            "distribution-release",
        ],
        version=ver,
        latest=ver == max(PHP_VERSIONS),
        env={
            "PHP_VERSION": {7: "7.4.25", 8: "8.0.10"}[ver],
            "COMPOSER_VERSION": "1.10.22",
        },
    )
    for ver in PHP_VERSIONS
)


RUST_VERSIONS = ["1.56", "1.57"]
(RUST_1_56, RUST_1_57) = (
    LanguageStackContainer(
        name="rust",
        pretty_name=f"Rust {rust_version}",
        latest=rust_version == "1.57",
        package_list=[
            f"rust{rust_version}",
            f"cargo{rust_version}",
            "distribution-release",
        ],
        version=rust_version,
        env={"RUST_VERSION": rust_version},
    )
    for rust_version in RUST_VERSIONS
)


def write_template_to_dir(bci: BaseContainerImage, dest: str, sp_version: int) -> None:
    with open(os.path.join(dest, "Dockerfile"), "w") as dockerfile:
        dockerfile.write(DOCKERFILE_TEMPLATE.render(image=bci, sp_version=sp_version))
    with open(os.path.join(dest, "_service"), "w") as service:
        service.write(_SERVICE)

    if not glob.glob(f"{dest}/*.changes"):
        with open(os.path.join(dest, f"{bci.nvr}-image.changes"), "w") as changesfile:
            changesfile.write("")

    for fname, contents in bci.extra_files.items():
        mode = "w" if isinstance(contents, str) else "b"
        with open(os.path.join(dest, fname), mode) as f:
            f.write(contents)


if __name__ == "__main__":
    ALL_IMAGES = {
        bci.nvr: bci
        for bci in (
            GOLANG_1_17,
            GOLANG_1_16,
            INIT,
            NODEJS_14,
            NODEJS_12,
            OPENJDK_11,
            OPENJDK_11_DEVEL,
            PYTHON_3_6,
            PYTHON_3_9,
            RUBY_2_5,
            PHP_7,
            PHP_8,
            THREE_EIGHT_NINE_DS,
            MARIADB,
            RMT_CONTAINER,
            POSTGRES_14,
            POSTGRES_13,
            POSTGRES_12,
            POSTGRES_10,
            NGINX,
            RUST_1_56,
            RUST_1_57,
        )
    }

    import argparse

    parser = argparse.ArgumentParser(
        description="Create the build description for SLE BCI packages"
    )
    parser.add_argument("sp_version", nargs=1, type=int, choices=[3, 4])
    parser.add_argument("bci", nargs=1, type=str, choices=list(ALL_IMAGES.keys()))
    parser.add_argument("dest_folder", nargs=1, type=str)

    args = parser.parse_args()
    write_template_to_dir(
        sp_version=args.sp_version[0],
        dest=args.dest_folder[0],
        bci=ALL_IMAGES[args.bci[0]],
    )
