"""V2 monitoring contracts. No synthetic observation can enter this layer."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import pandas as pd


@dataclass(frozen=True)
class Quote:
    security_id: str
    price: float
    previous_close: float | None
    observed_at: datetime
    currency: str
    source: str
    frequency: str = 'delayed / indicative'
    stats: dict = field(default_factory=dict)
    session: dict = field(default_factory=dict)

    @property
    def change(self):
        return None if self.previous_close is None else self.price-self.previous_close

    @property
    def change_pct(self):
        return None if self.previous_close in (None,0) else self.change/self.previous_close*100


@dataclass(frozen=True)
class HistoricalPrices:
    security_id: str
    frame: pd.DataFrame
    source: str
    interval: str
    adjusted: bool


@dataclass(frozen=True)
class DataResult:
    value: Any = None
    status: str = 'unavailable'
    retrieved_at: datetime | None = None
    attempted_at: datetime | None = None
    message: str = ''


@dataclass(frozen=True)
class NewsArticle:
    headline: str
    source: str
    published_at: datetime | None
    url: str
    description: str = ''
    securities: tuple = ()
    category: str = 'Macro'
    region: str = 'Global'


@dataclass(frozen=True)
class Event:
    title: str
    when: datetime
    source: str
    url: str
    security_id: str = ''
    timing: str = 'scheduled'


@dataclass(frozen=True)
class Fundamentals:
    security_id: str
    fields: dict
    source: str
