from staging.user import User


def test_user_from_xml():
    assert (
        User.from_xml(
            """<person>
  <login>dancermak</login>
  <email>me@foo.com</email>
  <realname>Dan Čermák</realname>
  <state>confirmed</state>
  <watchlist/>
</person>
"""
        )
        == User(login="dancermak", email="me@foo.com", realname="Dan Čermák")
    )
