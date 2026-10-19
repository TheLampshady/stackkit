"""Smoke tests for agent_service app_settings."""

from unittest.mock import patch


@patch("gcp_services.gcp_secrets.load_secrets")
@patch("gcp_services.IS_GCP", False)
def test_settings_instantiates_with_defaults(mock_secrets):
    """Settings class should instantiate with local defaults."""
    with patch.dict("os.environ", {"USE_EMULATOR": "True"}):
        from app_settings import Settings

        s = Settings()
        assert s.is_local is True
        assert s.is_gcp is False
        assert s.use_emulator is True


@patch("gcp_services.gcp_secrets.load_secrets")
@patch("gcp_services.IS_GCP", False)
def test_settings_has_no_frontend_fields(mock_secrets):
    """Agent settings should not have frontend-specific fields."""
    from app_settings import Settings

    s = Settings()
    assert not hasattr(s, "static_dir")
    assert not hasattr(s, "front_end_url")
    assert not hasattr(s, "spa_asset_folder")
    assert not hasattr(s, "firestore_bucket_name")
