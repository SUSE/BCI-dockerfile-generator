def test_entrypoint_docker_none(bci):
    cls, kwargs = bci
    c = cls(entrypoint=None, **kwargs)

    assert c.entrypoint_docker is None


def test_entrypoint_docker_string(bci):
    cls, kwargs = bci
    c = cls(entrypoint="/bin/foo", **kwargs)

    assert c.entrypoint_docker == "ENTRYPOINT /bin/foo"


def test_entrypoint_docker_list(bci):
    cls, kwargs = bci
    c = cls(entrypoint=["/bin/foo", "-a"], **kwargs)

    assert c.entrypoint_docker == "ENTRYPOINT ['/bin/foo', '-a']"


def test_entrypoint_kiwi_none(bci):
    cls, kwargs = bci
    c = cls(entrypoint=None, **kwargs)

    assert c.entrypoint_kiwi is None


def test_entrypoint_kiwi_string(bci):
    cls, kwargs = bci
    c = cls(entrypoint="/bin/foo", **kwargs)

    assert c.entrypoint_kiwi == '        <entrypoint execute="/bin/foo"/>'


def test_entrypoint_kiwi_list(bci):
    cls, kwargs = bci
    c = cls(entrypoint=["/bin/foo", "-a", "-x", "/path/to/a/file"], **kwargs)

    assert (
        c.entrypoint_kiwi
        == """        <entrypoint execute="/bin/foo">
          <argument name="-a"/>
          <argument name="-x"/>
          <argument name="/path/to/a/file"/>
        </entrypoint>
"""
    )
