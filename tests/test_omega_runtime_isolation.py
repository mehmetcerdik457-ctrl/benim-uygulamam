"""Normal read-only API MUST NOT carry disposable DB administrator credentials."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_api_service_has_no_database_bootstrap_credentials():
    compose=(ROOT/"compose.omega.yml").read_text()
    api=compose.split("\n  tests:",1)[0]
    assert "OMEGA_DATABASE_URL" not in api
    assert "POSTGRES_PASSWORD" not in api
    assert '"127.0.0.1:18080:8080"' in compose
    assert '    ports:' not in compose.split("  api:",1)[1].split("  ingress:",1)[0]
    assert "OMEGA_MODE: mock" in api
    assert "internal: true" in compose
def test_api_image_does_not_ship_migration_runner():
    docker=(ROOT/"omega_mvi"/"Dockerfile").read_text()
    assert "COPY db " not in docker
    assert "USER 10001:10001" in docker
    runner=(ROOT/"omega_mvi"/"Dockerfile.test").read_text()
    assert "COPY db /app/db" in runner
