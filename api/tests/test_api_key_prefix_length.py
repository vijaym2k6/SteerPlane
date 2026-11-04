"""SQLite does not enforce column lengths, so the rest of this suite cannot see this."""

from api.app.models.api_key import APIKey, generate_api_key


def test_the_stored_prefix_fits_its_column():
    prefix = generate_api_key()[:14] + "..."
    assert len(prefix) <= APIKey.__table__.c.key_prefix.type.length
