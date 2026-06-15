from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    date: datetime.date
    home: str
    away: str
    home_goals: int
    away_goals: int
    tournament: str
    neutral: bool

    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"
