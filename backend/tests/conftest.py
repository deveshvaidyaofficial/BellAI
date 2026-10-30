import os
import pytest
from app.config import get_settings

# Ensure safe defaults for automated tests regardless of local .env contents
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BOLNA_MOCK"] = "true"
os.environ["BOLNA_WEBHOOK_SECRET"] = ""
get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("BOLNA_MOCK", "true")
    # By default, leave webhook secret empty so legacy test suites can post without headers.
    # Individual tests in test_webhook.py that test authentication override this explicitly.
    monkeypatch.setenv("BOLNA_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
