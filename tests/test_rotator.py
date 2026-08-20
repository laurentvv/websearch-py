"""Tests for engine rotation and fallback strategies."""

from unittest.mock import MagicMock
from websearch_py.engines.base import BaseSearchEngine
from websearch_py.models import RotationStrategy
from websearch_py.rotation import EngineRotator


class DummyEngine(BaseSearchEngine):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def search(self, query, **kwargs):
        return []


def test_fallback_priority_ordering():
    e1 = DummyEngine("engine1")
    e2 = DummyEngine("engine2")
    e3 = DummyEngine("engine3")

    rotator = EngineRotator([e1, e2, e3], strategy=RotationStrategy.FALLBACK_PRIORITY)

    # Always returns in original configured order
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine1", "engine2", "engine3"]
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine1", "engine2", "engine3"]


def test_round_robin_rotation():
    e1 = DummyEngine("engine1")
    e2 = DummyEngine("engine2")
    e3 = DummyEngine("engine3")

    rotator = EngineRotator([e1, e2, e3], strategy=RotationStrategy.ROUND_ROBIN)

    # First query starts with engine 1
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine1", "engine2", "engine3"]
    # Second query starts with engine 2
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine2", "engine3", "engine1"]
    # Third query starts with engine 3
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine3", "engine1", "engine2"]
    # Fourth query loops back to engine 1
    assert [e.name for e in rotator.get_ordered_engines()] == ["engine1", "engine2", "engine3"]


def test_random_rotation():
    e1 = DummyEngine("engine1")
    e2 = DummyEngine("engine2")
    e3 = DummyEngine("engine3")

    rotator = EngineRotator([e1, e2, e3], strategy=RotationStrategy.RANDOM)
    ordered = rotator.get_ordered_engines()

    assert len(ordered) == 3
    assert set(e.name for e in ordered) == {"engine1", "engine2", "engine3"}
