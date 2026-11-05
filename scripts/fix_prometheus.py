"""Compatibility check: metrics are now configured directly in mlops.api."""

from mlops.api import app

if __name__ == "__main__":
    assert any(getattr(route, "path", None) == "/metrics" for route in app.routes)
    print("Metrics endpoint already configured; no source changes needed.")
