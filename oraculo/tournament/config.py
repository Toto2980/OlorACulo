from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class WorldCupConfig:
    seed: int
    groups: dict[str, list[str]]

    @property
    def teams(self) -> list[str]:
        return [team for teams in self.groups.values() for team in teams]


def load_config(path: str | Path) -> WorldCupConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    groups = {name: list(teams) for name, teams in data["groups"].items()}
    return WorldCupConfig(seed=int(data["seed"]), groups=groups)
