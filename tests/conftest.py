from typing import List, Tuple, Type, Generator, TypedDict, Union
from _pytest.python import Metafunc
from _pytest.fixtures import SubRequest
import pytest

from bci_build.package import (
    ApplicationStackContainer,
    BaseContainerImage,
    LanguageStackContainer,
    OsContainer,
    OsVersion,
)


BCI_CLASSES = [OsContainer, LanguageStackContainer, ApplicationStackContainer]


class BciKwargsBase(TypedDict):
    name: str
    pretty_name: str
    package_name: str
    os_version: OsVersion
    package_list: List[str]


class BciKwargs(BciKwargsBase):
    version: str


KWARGS = BciKwargsBase(
    name="test",
    pretty_name="Test",
    package_name="test-image",
    os_version=OsVersion.SP4,
    package_list=["cat"],
)


BCI_FIXTURE_RET_T = Tuple[Type[BaseContainerImage], Union[BciKwargs, BciKwargsBase]]


@pytest.fixture
def bci(request: SubRequest) -> Generator[BCI_FIXTURE_RET_T, None, None]:
    p = request.param if request.param in BCI_CLASSES else request.param[0]

    if p == LanguageStackContainer or p == ApplicationStackContainer:
        kwargs: BciKwargs = {**KWARGS, "version": "1.0"}
        yield p, kwargs
    else:
        yield p, {**KWARGS}


def pytest_generate_tests(metafunc: Metafunc):
    if "bci" in metafunc.fixturenames:
        metafunc.parametrize("bci", BCI_CLASSES, indirect=True)
