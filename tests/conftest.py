"""Shared fixtures for the test suite."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def project_root():
    return ROOT


@pytest.fixture(scope="session")
def config_dir():
    return ROOT / "config"


@pytest.fixture(scope="session")
def raw_data_dir():
    return ROOT / "data" / "entities"


@pytest.fixture(scope="session")
def normalized_entities_path(raw_data_dir, tmp_path_factory):
    from taskgen.normalizer import normalize_all, save_normalized
    tmp = tmp_path_factory.mktemp("data")
    out = tmp / "entities.json"
    entities = normalize_all(raw_data_dir)
    save_normalized(entities, out)
    return out


@pytest.fixture(scope="session")
def entities(normalized_entities_path):
    from taskgen.loaders import load_entities
    return load_entities(normalized_entities_path)


@pytest.fixture(scope="session")
def runtime_ctx(config_dir, normalized_entities_path):
    from taskgen.loaders import RuntimeContext
    return RuntimeContext(
        config_dir=config_dir,
        entities_path=normalized_entities_path,
    )


@pytest.fixture
def fake_provider():
    from taskgen.llm.fake import FakeProvider
    return FakeProvider()
