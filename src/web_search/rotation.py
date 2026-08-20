"""Engine rotation and fallback orchestration strategies."""

from __future__ import annotations

import itertools
import logging
import random
import threading
from typing import Sequence

from web_search.engines.base import BaseSearchEngine
from web_search.models import RotationStrategy

logger = logging.getLogger(__name__)


class EngineRotator:
    """Manages the ordering and rotation of search engines according to selected strategy."""

    def __init__(
        self,
        engines: Sequence[BaseSearchEngine],
        strategy: RotationStrategy | str = RotationStrategy.FALLBACK_PRIORITY,
    ):
        """Initialize EngineRotator.

        Args:
            engines: List of instantiated BaseSearchEngine instances.
            strategy: RotationStrategy enum or string name.
        """
        if not engines:
            raise ValueError("EngineRotator requires at least one engine.")

        self.engines = list(engines)
        if isinstance(strategy, str):
            strategy = RotationStrategy(strategy)
        self.strategy = strategy
        self._round_robin_index = 0
        self._lock = threading.Lock()

    def get_ordered_engines(self) -> list[BaseSearchEngine]:
        """Return engines in the order they should be attempted for a new search query."""
        n = len(self.engines)
        if n == 1:
            return list(self.engines)

        if self.strategy == RotationStrategy.FALLBACK_PRIORITY:
            # Fixed order
            return list(self.engines)

        elif self.strategy == RotationStrategy.ROUND_ROBIN:
            # Shift starting engine circularly
            with self._lock:
                start_idx = self._round_robin_index % n
                self._round_robin_index = (self._round_robin_index + 1) % n

            return self.engines[start_idx:] + self.engines[:start_idx]

        elif self.strategy == RotationStrategy.RANDOM:
            # Random starting engine, followed by the rest in random or shifted order
            shuffled = list(self.engines)
            random.shuffle(shuffled)
            return shuffled

        elif self.strategy == RotationStrategy.FASTEST:
            # All engines concurrently
            return list(self.engines)

        return list(self.engines)

    def set_strategy(self, strategy: RotationStrategy | str) -> None:
        """Update active rotation strategy."""
        if isinstance(strategy, str):
            strategy = RotationStrategy(strategy)
        self.strategy = strategy
