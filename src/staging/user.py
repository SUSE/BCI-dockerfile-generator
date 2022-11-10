import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class User:
    login: str
    email: str
    realname: str

    @classmethod
    def from_xml(cls, xml_element: ET.Element | str) -> "User":
        elem = (
            xml_element
            if isinstance(xml_element, ET.Element)
            else ET.fromstring(xml_element)
        )

        kwargs = {"login": "", "email": "", "realname": ""}
        if (tag := elem.tag) != "person":
            raise ValueError(f"Invalid tag, expected 'person', but got '{tag}'")

        for child in elem:
            if (tag := child.tag) in kwargs.keys():
                if not child.text:
                    raise ValueError(f"Element {tag} is missing an entry")
                kwargs[tag] = child.text

        for key, val in kwargs.items():
            if not val:
                raise ValueError(f"Entry for {key} missing in response from OBS")

        return cls(**kwargs)
