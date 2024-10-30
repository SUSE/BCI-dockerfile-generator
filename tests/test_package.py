from bci_build.container_attributes import TCP
from bci_build.container_attributes import UDP
from tests.conftest import BCI_FIXTURE_RET_T


def test_entrypoint_docker_none(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(entrypoint=None, **kwargs)

    assert c.entrypoint_docker is None


def test_entrypoint_docker_list(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(entrypoint=["/bin/foo", "-a"], **kwargs)

    assert (
        c.entrypoint_docker
        == """
ENTRYPOINT ["/bin/foo", "-a"]"""
    )


def test_entrypoint_kiwi_none(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(entrypoint=None, **kwargs)

    assert c.entrypoint_kiwi is None


def test_entrypoint_kiwi_single_entry(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(entrypoint=["/bin/foo"], **kwargs)

    assert c.entrypoint_kiwi
    assert c.entrypoint_kiwi.lstrip() == '<entrypoint execute="/bin/foo"/>'


def test_entrypoint_kiwi_list(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(entrypoint=["/bin/foo", "-a", "-x", "/path/to/a/file"], **kwargs)

    assert c.entrypoint_kiwi
    assert (
        c.entrypoint_kiwi.lstrip()
        == """<entrypoint execute="/bin/foo">
          <argument name="-a"/>
          <argument name="-x"/>
          <argument name="/path/to/a/file"/>
        </entrypoint>
"""
    )


def test_no_volumes_kiwi(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(**kwargs, volumes=[])

    assert c.volumes_kiwi == ""


def test_single_volume_kiwi(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(**kwargs, volumes=["/foo/bar"])

    assert (
        c.volumes_kiwi
        == """
        <volumes>
          <volume name="/foo/bar" />
        </volumes>"""
    )


def test_multiple_volumes_kiwi(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci
    c = cls(**kwargs, volumes=["/foo/bar", "/proc/"])

    assert (
        c.volumes_kiwi
        == """
        <volumes>
          <volume name="/foo/bar" />
          <volume name="/proc/" />
        </volumes>"""
    )


def test_no_expose_kiwi(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert cls(**kwargs, exposes_ports=[]).exposes_kiwi == ""
    assert cls(**kwargs).exposes_kiwi == ""
    assert cls(**kwargs, exposes_ports=None).exposes_kiwi == ""


def test_expose_port_kiwi(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert (
        cls(**kwargs, exposes_ports=[TCP(443), TCP(80)]).exposes_kiwi
        == """
        <expose>
          <port number="443/tcp" />
          <port number="80/tcp" />
        </expose>"""
    )


def test_no_expose_dockerfile(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert cls(**kwargs).expose_dockerfile == ""
    assert cls(**kwargs, exposes_ports=[]).expose_dockerfile == ""
    assert cls(**kwargs, exposes_ports=None).expose_dockerfile == ""


def test_expose_dockerfile(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert (
        cls(**kwargs, exposes_ports=[TCP(80), TCP(443), UDP(67)]).expose_dockerfile
        == "\nEXPOSE 80/tcp 443/tcp 67/udp"
    )


def test_no_volume_dockerfile(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert cls(**kwargs).volume_dockerfile == ""
    assert cls(**kwargs, volumes=[]).volume_dockerfile == ""
    assert cls(**kwargs, volumes=None).volume_dockerfile == ""


def test_volume_dockerfile(bci: BCI_FIXTURE_RET_T):
    cls, kwargs = bci

    assert (
        cls(**kwargs, volumes=["/var/log", "/sys/"]).volume_dockerfile
        == "\nVOLUME /var/log /sys/"
    )
