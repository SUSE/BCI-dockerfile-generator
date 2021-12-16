#!/usr/bin/env python3

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
class BaseContainerImage:
    name: str

    #: Human readable name that will be inserted into the image title and description
    pretty_name: str

    #: The version tag of this container.
    #: If omitted, then the OS version will be used in the :file:`Dockerfile`
    version: Optional[str] = None

    #: The container from which this one is derived. defaults to
    #: ``suse/sle15:15.$SP``
    from_image: Optional[str] = None

    #: an optional entrypoint for the image, is omitted if empty or ``None``
    entrypoint: Optional[str] = None

    #: Extra environment variables to be set in the container
    env: Dict[str, str] = field(default_factory=dict)

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

    def __post_init__(self) -> None:
        if not self.package_list:
            raise ValueError(f"No packages were added to {self.pretty_name}.")

    @property
    def nvr(self) -> str:
        return self.name + (f"-{self.version}" if self.version else "")

    @property
    def version_label(self) -> str:
        return self.version if self.version else "%OS_VERSION_ID_SP%.%RELEASE%"

    @property
    def packages(self) -> str:
        return " ".join(self.package_list)

    @property
    def env_lines(self) -> str:
        return "\n".join(f'ENV {k}="{v}"' for k, v in self.env.items())

    @property
    def build_tag(self) -> str:
        return f"bci/{self.name}:{self.version_label}"

    @property
    def reference(self) -> str:
        return f"registry.suse.com/{self.build_tag}"

    @property
    def description(self) -> str:
        return f"Image containing {self.pretty_name} based on the SLE Base Container Image."

    @property
    def title(self) -> str:
        return f"SLE BCI {self.pretty_name} container"

    @property
    def extra_label_lines(self) -> str:
        return "\n".join(f'LABEL {k}="{v}"' for k, v in self.extra_labels.items())


PYTHON_3_6 = BaseContainerImage(
    name="python",
    pretty_name="Python",
    version="3.6",
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

PYTHON_3_9 = BaseContainerImage(
    name="python",
    pretty_name="Python 3.9",
    version="3.9",
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

RUBY_2_5 = BaseContainerImage(
    name="ruby",
    pretty_name="Ruby 2.5",
    version="2.5",
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
    BaseContainerImage(
        name="golang",
        pretty_name=f"Golang {ver}",
        version=ver,
        env={
            "GOLANG_VERSION": ver,
            "PATH": "/go/bin:/usr/local/go/bin:/root/go/bin/:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        },
        package_list=[f"go{ver}", "distribution-release"],
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

(NODEJS_12, NODEJS_14) = (
    BaseContainerImage(
        name="nodejs",
        version=ver,
        pretty_name=f"Node.js {ver}",
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
    for ver in ("12", "14")
)

JAVA_ENV = {
    "JAVA_BINDIR": "/usr/lib64/jvm/java/bin",
    "JAVA_HOME": "/usr/lib64/jvm/java",
    "JAVA_ROOT": "/usr/lib64/jvm/java",
    "JAVA_VERSION": "11",
}
OPENJDK_11 = BaseContainerImage(
    name="openjdk",
    pretty_name="OpenJDK 11",
    version="11",
    package_list=["java-11-openjdk"],
    env=JAVA_ENV,
)
OPENJDK_11_DEVEL = BaseContainerImage(
    name="openjdk.devel",
    pretty_name="OpenJDK 11 development",
    version="11",
    package_list=["java-11-openjdk-devel", "git-core", "maven"],
    entrypoint="jshell",
    from_image="bci/openjdk:11",
    env=JAVA_ENV,
)

INIT = BaseContainerImage(
    name="init",
    pretty_name="Systemd",
    package_list=["systemd"],
    extra_labels={
        "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
    },
)

with open(
    os.path.join(os.path.dirname(__file__), "mariadb-entrypoint.sh")
) as entrypoint:
    MARIADB = BaseContainerImage(
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
    RMT_CONTAINER = BaseContainerImage(
        name="rmt-server",
        maintainer="bruno.leon@suse.de",
        pretty_name="RMT Server",
        package_list=["rmt-server", "catatonit"],
        entrypoint="/usr/local/bin/entrypoint.sh",
        env={"RAILS_ENV": "production", "LANG": "en"},
        extra_files={"entrypoint.sh": entrypoint.read(-1)},
        custom_end="""COPY entrypoint.sh /usr/local/bin/entrypoint.sh
CMD ["/usr/share/rmt/bin/rails", "server", "-e", "production"]
""",
    )


THREE_EIGHT_NINE_DS = BaseContainerImage(
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

(PHP_7, PHP_8) = (
    BaseContainerImage(
        name=f"php",
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
        env={
            "PHP_VERSION": {"7": "7.4.25", "8": "8.0.10"}[ver],
            "COMPOSER_VERSION": "1.10.22",
        },
    )
    for ver in ("7", "8")
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
