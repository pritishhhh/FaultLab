from faultlab.config import Settings


def test_managed_database_url_encodes_password():
    config = Settings(_env_file=None, db_host="db.internal", db_password="a@b/c")
    assert "a%40b%2Fc" in config.database_url
    assert "sslmode=require" in config.database_url
