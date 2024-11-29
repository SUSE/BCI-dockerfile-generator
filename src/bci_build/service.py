"""This module includes an abstraction over source services in the Open Build
Service.

"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from typing import Literal


@dataclass(kw_only=True, frozen=True)
class Service:
    """Representation of an arbitrary source service in the Open Build Service."""

    #: name of this service
    name: str

    #: unsorted list of parameters of this source service as a list of tuples
    #: where the first value is the parameter's name and the second is the
    #: parameter's value
    param: list[tuple[str, str]] = field(default_factory=list)

    #: service mode (i.e. when the service runs)
    mode: Literal["buildtime"] = "buildtime"

    def as_xml_element(self) -> ET.Element:
        """Converts this source service into a
        :py:class:`~xml.etree.ElementTree.Element`.

        """
        root = ET.Element("service", attrib={"name": self.name, "mode": self.mode})

        for param in self.param:
            (p := ET.Element("param", attrib={"name": param[0]})).text = param[1]
            root.append(p)

        ET.indent(root, space=" " * 4)
        return root

    def __str__(self) -> str:
        return ET.tostring(self.as_xml_element(), encoding="unicode")
