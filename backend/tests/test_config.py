from app.core.config import settings


def test_settings():
    assert settings.app_name == "Topcoder Combinator"
    assert settings.llm_provider == "mock"
    assert settings.starter_pack_path.name == "starter-pack"
    assert settings.workspace_path.name == "workspace"