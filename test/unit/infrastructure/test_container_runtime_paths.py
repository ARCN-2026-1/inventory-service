import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_dockerfile_sets_stable_pythonpath_for_runtime_processes() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ENV PYTHONPATH=/app" in dockerfile


def test_prod_compose_pins_working_dir_and_pythonpath_for_all_services() -> None:
    compose = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "x-inventory-env: &inventory-env" in compose
    assert "- PYTHONPATH=/app" in compose

    for service_name in ("inventory-migration", "inventory-api", "inventory-worker"):
        pattern = rf"^  {service_name}:\n(?P<body>(?:    .*(?:\n|$))+)"
        match = re.search(pattern, compose, flags=re.MULTILINE)
        assert match is not None
        service_block = match.group("body")
        assert "working_dir: /app" in service_block
        assert "environment: *inventory-env" in service_block
