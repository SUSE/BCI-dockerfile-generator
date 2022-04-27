from typing import Dict, Tuple, Type, Generator
from _pytest.python import Metafunc
from _pytest.fixtures import SubRequest
import pytest

from bci_build.package import (
    ApplicationStackContainer,
    BaseContainerImage,
    LanguageStackContainer,
    OsContainer,
)


BCI_CLASSES = [OsContainer, LanguageStackContainer, ApplicationStackContainer]

KWARGS = {
    "name": "test",
    "pretty_name": "Test",
    "package_name": "test-image",
    "os_version": 4,
    "package_list": ["cat"],
}


@pytest.fixture
def bci(
    request: SubRequest,
) -> Generator[Tuple[Type[BaseContainerImage], Dict[str, str]], None, None]:
    kwargs = {**KWARGS}
    p = request.param if request.param in BCI_CLASSES else request.param[0]
    if p == LanguageStackContainer or p == ApplicationStackContainer:
        kwargs["version"] = "1.0"
    yield p, kwargs


def pytest_generate_tests(metafunc: Metafunc):
    if "bci" in metafunc.fixturenames:
        metafunc.parametrize("bci", BCI_CLASSES, indirect=True)
