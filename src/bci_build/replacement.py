from dataclasses import dataclass

from bci_build.service import Service
from bci_build.util import ParseVersion


@dataclass
class Replacement:
    """Represents a replacement via the `obs-service-replace_using_package_version
    <https://github.com/openSUSE/obs-service-replace_using_package_version>`_.

    """

    #: regex to be replaced in :py:attr:`~bci_build.package.Replacement.file_name`, :file:`Dockerfile` or :file:`$pkg_name.kiwi`
    regex_in_build_description: str

    #: package name to be queried for the version
    package_name: str

    #: override file name, if unset use :file:`Dockerfile` or :file:`$pkg_name.kiwi`
    file_name: str | None = None

    #: specify how the version should be formatted, see
    #: `<https://github.com/openSUSE/obs-service-replace_using_package_version#usage>`_
    #: for further details
    parse_version: None | ParseVersion = None

    def __post_init__(self) -> None:
        """Barf if someone tries to replace variables in README, as those
        changes will be only performed in the buildroot, but not in the actual
        source package.

        """
        if "%%" not in self.regex_in_build_description:
            raise ValueError("regex_in_build_description must be in the form %%foo%%")
        if self.file_name and "readme" in self.file_name.lower():
            raise ValueError(f"Cannot replace variables in {self.file_name}!")

    def to_service(self, default_file_name: str) -> Service:
        """Convert this replacement into a
        :py:class:`~bci__build.service.Service`.

        """
        return Service(
            name="replace_using_package_version",
            param=[
                ("file", self.file_name or default_file_name),
                ("regex", self.regex_in_build_description),
                ("package", self.package_name),
            ]
            + ([("parse-version", self.parse_version)] if self.parse_version else []),
        )
