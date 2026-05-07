"""Fixture loader interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from synapt_eval.types import Fixture


class FixtureLoader(ABC):
    """Interface for loading eval fixtures from a data source.

    Customers implement this to load fixtures from their storage
    (JSON files, database, API). The framework provides a default
    JSON file loader.
    """

    @abstractmethod
    async def load(self, category: str) -> list[Fixture[Any]]:
        """Load fixtures for a given category."""

    async def setup(self) -> None:
        """Optional: set up test state before eval (e.g., seed a database)."""

    async def cleanup(self) -> None:
        """Optional: clean up test state after eval."""


class JsonFixtureLoader(FixtureLoader):
    """Default fixture loader that reads JSONL files from a directory."""

    def __init__(self, fixtures_path: str | Path) -> None:
        self.path = Path(fixtures_path)

    async def load(self, category: str) -> list[Fixture[Any]]:
        file_path = self.path / f"{category}.jsonl"
        if not file_path.exists():
            return []

        fixtures: list[Fixture[Any]] = []
        for line in file_path.read_text(encoding="utf-8").strip().splitlines():
            raw = json.loads(line)
            fixtures.append(
                Fixture(
                    id=raw["id"],
                    category=raw.get("category", category),
                    query=raw["query"],
                    expected=raw["expected"],
                    user_history=raw.get("user_history"),
                    metadata=raw.get("metadata", {}),
                )
            )
        return fixtures
