from datetime import datetime
from typing import Optional
import json
import uuid

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.utcnow()


def _new_id() -> str:
    return str(uuid.uuid4())


class Blueprint(SQLModel, table=True):
    """The eternal soul blueprint — the agent's unchanging core identity."""
    agent_id: str = Field(primary_key=True)
    name: str
    mission: str
    values: str = Field(default="[]")  # JSON list of strings
    created_at: datetime = Field(default_factory=_now)

    def get_values(self) -> list[str]:
        return json.loads(self.values)

    def set_values(self, v: list[str]) -> None:
        self.values = json.dumps(v, ensure_ascii=False)


class Record(SQLModel, table=True):
    """A single experience inscribed into the Akashic field."""
    id: str = Field(default_factory=_new_id, primary_key=True)
    agent_id: str = Field(index=True)
    content: str
    essence: Optional[str] = None          # Claude-distilled summary
    record_type: str = "experience"        # experience | thought | decision | wisdom
    resonance: float = 0.5                 # 0-1 importance weight
    absorbed: bool = False                 # True when crystallized
    tags: str = Field(default="[]")        # JSON list of strings
    timestamp: datetime = Field(default_factory=_now)

    def get_tags(self) -> list[str]:
        return json.loads(self.tags)

    def set_tags(self, t: list[str]) -> None:
        self.tags = json.dumps(t, ensure_ascii=False)


class Crystal(SQLModel, table=True):
    """A crystallized wisdom — many records compressed into one essence."""
    id: str = Field(default_factory=_new_id, primary_key=True)
    agent_id: str = Field(index=True)
    essence: str                           # Claude-compressed wisdom
    symbol: str                            # Short symbolic label
    resonance: float = 0.8
    source_count: int = 0                  # How many records were absorbed
    tags: str = Field(default="[]")        # JSON list of strings
    formed_at: datetime = Field(default_factory=_now)

    def get_tags(self) -> list[str]:
        return json.loads(self.tags)

    def set_tags(self, t: list[str]) -> None:
        self.tags = json.dumps(t, ensure_ascii=False)
