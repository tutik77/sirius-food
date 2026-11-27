"""
Архитектурные тесты: правило зависимостей Clean Architecture.
"""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"
FORBIDDEN_IN_SERVICE = {"fastapi", "sqlalchemy", "starlette", "redis"}


def imported_packages(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    packages = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            packages |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            packages.add(node.module.split(".")[0])
    return packages


SERVICES = sorted([*APP.glob("modules/*/service.py"), APP.parent / "delivery_service" / "service.py"])


ROOT = APP.parent


def test_all_modules_have_three_layers():
    for module in ("auth", "users", "menu", "orders"):
        for layer in ("router.py", "service.py", "repository.py"):
            assert (APP / "modules" / module / layer).exists(), f"{module}/{layer}"


def test_delivery_is_extracted_to_grpc_service():
    for layer in ("router.py", "gateway.py", "grpc_client.py"):
        assert (APP / "modules" / "delivery" / layer).exists(), layer
    for layer in ("service.py", "repository.py", "server.py"):
        assert (ROOT / "delivery_service" / layer).exists(), layer
    assert (ROOT / "proto" / "delivery.proto").exists()


def test_monolith_does_not_touch_delivery_storage():
    for path in (APP / "modules" / "delivery").glob("*.py"):
        assert "delivery_service" not in imported_packages(path), path.name


@pytest.mark.parametrize("service", SERVICES, ids=lambda p: p.parent.name)
def test_service_does_not_import_frameworks(service):
    assert not imported_packages(service) & FORBIDDEN_IN_SERVICE


@pytest.mark.parametrize("path", sorted((APP / "domain").glob("*.py")), ids=lambda p: p.name)
def test_domain_layer_is_framework_free(path):
    assert not imported_packages(path) & FORBIDDEN_IN_SERVICE


def test_ci_must_block_merge_when_red():
    assert 1 == 2
