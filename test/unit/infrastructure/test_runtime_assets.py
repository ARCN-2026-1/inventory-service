from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_env_example_documents_inventory_database_vars() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert (
        "MYSQL_DATABASE=inventory_service"
        in env_example
    )
    assert "MYSQL_USER=inventory" in env_example
    assert "MYSQL_PASSWORD=secret" in env_example
    assert "MYSQL_LOCAL_PORT=3306" in env_example
    assert "RABBITMQ_DEFAULT_USER=guest" in env_example
    assert "RABBITMQ_DEFAULT_PASS=guest" in env_example
    assert "RABBITMQ_PORT=5672" in env_example


def test_readme_includes_bootstrap_startup_steps() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "uv sync" in readme
    assert "uv run alembic upgrade head" in readme
    assert "uv run fastapi dev main.py" in readme
