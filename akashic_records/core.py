"""
AkashicRecords — the main interface to the soul's eternal archive.

Usage:
    records = AkashicRecords(agent_id="seeker", anthropic_api_key="...")
    await records.set_blueprint(mission="...", values=[...])
    await records.inscribe("Today I learned...", resonance=0.8, tags=["learning"])

    async with records.ritual(intention="understand my patterns") as session:
        emerged = await session.receive(n=5, temperature=0.8)
        revelation = await session.insight()
        print(revelation)

    crystals = await records.get_crystals()
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from .crystallizer import Crystallizer
from .models import Blueprint, Crystal, Record
from .sampler import SamplerEntry, resonance_sample
from .scribe import Scribe
from .store import AkashicStore


class RitualSession:
    """
    A ritual access session — the structured process of reading the Akashic field.

    Phase 1 (open):  Blueprint loaded, intention set
    Phase 2 (connect): Field scanned for resonant entries
    Phase 3 (receive): Serendipitous emergence via weighted sampling
    Phase 4 (close):  Revelation written back as wisdom record
    """

    def __init__(
        self,
        agent_id: str,
        intention: str,
        store: AkashicStore,
        scribe: Scribe,
        crystallizer: Crystallizer,
        blueprint: Optional[Blueprint],
    ):
        self._agent_id = agent_id
        self._intention = intention
        self._store = store
        self._scribe = scribe
        self._crystallizer = crystallizer
        self._blueprint = blueprint

        self._emerged_records: list[Record] = []
        self._emerged_crystals: list[Crystal] = []
        self._revelation: Optional[str] = None
        self._new_crystals: list[Crystal] = []

    async def receive(
        self,
        n: int = 5,
        temperature: float = 0.7,
        half_life_days: float = 30.0,
        include_crystals: bool = True,
    ) -> list[Record]:
        """
        Open the field and let records emerge.
        Returns the records that surfaced — not necessarily the most relevant,
        but shaped by resonance, time, and a touch of cosmic chance.
        """
        # Query vector field for semantic scores
        vector_hits = self._store.query_vector(
            agent_id=self._agent_id,
            query_text=self._intention,
            n_results=50,
        )
        hit_map = {rid: dist for rid, dist in vector_hits}

        # Build sampler entries from all active records
        all_records = self._store.get_all_records(self._agent_id)
        entries = []
        for r in all_records:
            # Convert distance to similarity score (closer = higher score)
            dist = hit_map.get(r.id, 2.0)
            semantic_score = max(0.0, 1.0 - dist / 2.0)
            entries.append(SamplerEntry(
                id=r.id,
                resonance=r.resonance,
                timestamp=r.timestamp,
                semantic_score=semantic_score,
            ))

        sampled = resonance_sample(
            entries=entries,
            k=n,
            temperature=temperature,
            half_life_days=half_life_days,
        )
        sampled_ids = {e.id for e in sampled}

        self._emerged_records = [r for r in all_records if r.id in sampled_ids]

        # Also surface crystals if requested
        if include_crystals:
            crystal_hits = self._store.query_crystals_vector(
                agent_id=self._agent_id,
                query_text=self._intention,
                n_results=min(3, n // 2 + 1),
            )
            all_crystals = self._store.get_all_crystals(self._agent_id)
            crystal_map = {c.id: c for c in all_crystals}
            self._emerged_crystals = [
                crystal_map[cid] for cid, _ in crystal_hits if cid in crystal_map
            ]

        return self._emerged_records

    async def insight(self) -> str:
        """
        Ask the Scribe to synthesize a revelation from what emerged.
        This is the 'reading of the records' — Claude interprets the field.
        """
        if not self._emerged_records and not self._emerged_crystals:
            await self.receive()

        self._revelation = await asyncio.to_thread(
            self._scribe.reveal,
            intention=self._intention,
            emerged_records=self._emerged_records,
            emerged_crystals=self._emerged_crystals,
            blueprint=self._blueprint,
        )
        return self._revelation

    async def _close(self) -> None:
        """Write the revelation back as a wisdom record. Check for crystallization."""
        if self._revelation:
            wisdom_record = Record(
                agent_id=self._agent_id,
                content=self._revelation,
                record_type="wisdom",
                resonance=0.9,
            )
            wisdom_record.set_tags(["ritual_wisdom", "revelation"])
            self._store.insert_record(wisdom_record)

        # Check if crystallization should occur
        self._new_crystals = await asyncio.to_thread(
            self._crystallizer.check_and_crystallize,
            agent_id=self._agent_id,
            blueprint=self._blueprint,
        )

    @property
    def new_crystals(self) -> list[Crystal]:
        return self._new_crystals


class AkashicRecords:
    """The eternal archive — entry point for all agent memory operations."""

    def __init__(
        self,
        agent_id: str,
        anthropic_api_key: str,
        data_dir: str = ".akashic",
        model: str = "claude-sonnet-4-6",
        crystallization_threshold: int = 8,
    ):
        self._agent_id = agent_id
        self._store = AkashicStore(data_dir=data_dir)
        self._scribe = Scribe(api_key=anthropic_api_key, model=model)
        self._crystallizer = Crystallizer(
            store=self._store,
            scribe=self._scribe,
            threshold=crystallization_threshold,
        )

    # ------------------------------------------------------------------ #
    # Blueprint                                                            #
    # ------------------------------------------------------------------ #

    async def set_blueprint(
        self,
        name: str = "Agent",
        mission: str = "",
        values: Optional[list[str]] = None,
    ) -> Blueprint:
        """Define or update the soul's eternal blueprint."""
        bp = Blueprint(
            agent_id=self._agent_id,
            name=name,
            mission=mission,
        )
        bp.set_values(values or [])
        await asyncio.to_thread(self._store.save_blueprint, bp)
        return bp

    def _load_blueprint(self) -> Optional[Blueprint]:
        return self._store.load_blueprint(self._agent_id)

    # ------------------------------------------------------------------ #
    # Inscribing                                                           #
    # ------------------------------------------------------------------ #

    async def inscribe(
        self,
        content: str,
        record_type: str = "experience",
        resonance: float = 0.5,
        tags: Optional[list[str]] = None,
        distill: bool = False,
    ) -> Record:
        """
        Inscribe an experience into the eternal field.

        distill=True: ask Claude to distill the content to its essence first.
        """
        blueprint = await asyncio.to_thread(self._load_blueprint)

        essence = None
        if distill:
            essence = await asyncio.to_thread(
                self._scribe.distill, content, blueprint
            )

        record = Record(
            agent_id=self._agent_id,
            content=content,
            essence=essence,
            record_type=record_type,
            resonance=max(0.0, min(1.0, resonance)),
        )
        record.set_tags(tags or [])
        await asyncio.to_thread(self._store.insert_record, record)

        # Passive crystallization check after each inscription
        await asyncio.to_thread(
            self._crystallizer.check_and_crystallize,
            self._agent_id,
            blueprint,
        )

        return record

    # ------------------------------------------------------------------ #
    # Ritual access                                                        #
    # ------------------------------------------------------------------ #

    @asynccontextmanager
    async def ritual(self, intention: str):
        """
        Context manager for ritual access to the Akashic field.

        async with records.ritual("understand my patterns") as session:
            emerged = await session.receive(n=5, temperature=0.8)
            revelation = await session.insight()
        """
        blueprint = await asyncio.to_thread(self._load_blueprint)
        session = RitualSession(
            agent_id=self._agent_id,
            intention=intention,
            store=self._store,
            scribe=self._scribe,
            crystallizer=self._crystallizer,
            blueprint=blueprint,
        )
        try:
            yield session
        finally:
            await session._close()

    # ------------------------------------------------------------------ #
    # Querying                                                             #
    # ------------------------------------------------------------------ #

    async def get_records(self, include_absorbed: bool = False) -> list[Record]:
        return await asyncio.to_thread(
            self._store.get_all_records, self._agent_id, include_absorbed
        )

    async def get_crystals(self) -> list[Crystal]:
        return await asyncio.to_thread(
            self._store.get_all_crystals, self._agent_id
        )

    async def count(self) -> dict[str, int]:
        records = await self.get_records()
        crystals = await self.get_crystals()
        return {
            "active_records": len(records),
            "crystals": len(crystals),
            "total_crystallized": sum(c.source_count for c in crystals),
        }
