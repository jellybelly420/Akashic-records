"""
AkashicRecords — the main interface to the soul's eternal archive.

Three compression tiers:
  Experience → Record → (accumulate) → Crystal → (transcend) → Sigil

The ritual surfaces all three layers. Sigils are encrypted marks — nearly
unreadable alone. Only when held against an intention does their meaning unfold.

Usage:
    records = AkashicRecords(agent_id="seeker", anthropic_api_key="...")
    await records.set_blueprint(name="...", mission="...", values=[...])
    await records.inscribe("Today I learned...", resonance=0.8, tags=["learning"])

    async with records.ritual(intention="understand my patterns") as session:
        layers = await session.receive(n=5, temperature=0.8)
        revelation = await session.insight()
        print(revelation)

    sigils = await records.get_sigils()   # The encrypted archive
    crystals = await records.get_crystals()
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

from .crystallizer import Crystallizer
from .models import Blueprint, Crystal, Record, Sigil
from .sampler import SamplerEntry, resonance_sample
from .scribe import Scribe
from .store import AkashicStore


@dataclass
class EmergedLayers:
    """What surfaced during ritual — three layers of the field."""
    sigils: list[Sigil]
    crystals: list[Crystal]
    records: list[Record]

    def __bool__(self) -> bool:
        return bool(self.sigils or self.crystals or self.records)


class RitualSession:
    """
    A ritual access session — the structured process of reading the Akashic field.

    Phase 1 (enter):   Blueprint loaded, intention held
    Phase 2 (connect): Field scanned, semantic scores computed
    Phase 3 (receive): Serendipitous emergence — three layers surface
                       Sigils first (most encoded), then crystals, then records
    Phase 4 (decode):  Claude reads all layers against the intention
    Phase 5 (close):   Revelation inscribed as wisdom; crystallization checked
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

        self._layers = EmergedLayers(sigils=[], crystals=[], records=[])
        self._revelation: Optional[str] = None
        self._new_crystals: list[Crystal] = []
        self._new_sigils: list[Sigil] = []

    async def receive(
        self,
        n: int = 5,
        temperature: float = 0.7,
        half_life_days: float = 30.0,
    ) -> EmergedLayers:
        """
        Open the field. Three layers surface simultaneously:
        Sigils (most compressed), Crystals (medium), Records (raw).

        The mix is weighted by resonance and chance — never fully predictable.
        """
        # --- Sigils ---
        sigil_hits = self._store.query_sigils_vector(
            agent_id=self._agent_id,
            query_text=self._intention,
            n_results=5,
        )
        all_sigils = self._store.get_all_sigils(self._agent_id)
        sigil_map = {s.id: s for s in all_sigils}
        # Sigils always surface if they exist — they are the deepest encoded layer
        # Use resonance sampling with high weight (sigils carry much mass)
        sigil_entries = []
        sigil_dist_map = {sid: dist for sid, dist in sigil_hits}
        for s in all_sigils:
            dist = sigil_dist_map.get(s.id, 2.0)
            semantic_score = max(0.0, 1.0 - dist / 2.0)
            sigil_entries.append(SamplerEntry(
                id=s.id,
                resonance=s.resonance,
                timestamp=s.formed_at,
                semantic_score=semantic_score,
            ))
        sampled_sigils = resonance_sample(
            sigil_entries, k=min(2, len(sigil_entries)),
            temperature=temperature * 1.2,  # Sigils have extra randomness
            half_life_days=half_life_days * 3,  # Sigils decay much slower
        )
        self._layers.sigils = [sigil_map[e.id] for e in sampled_sigils if e.id in sigil_map]

        # --- Crystals ---
        crystal_hits = self._store.query_crystals_vector(
            agent_id=self._agent_id,
            query_text=self._intention,
            n_results=20,
        )
        all_crystals = self._store.get_all_crystals(self._agent_id)
        crystal_map = {c.id: c for c in all_crystals}
        crystal_dist_map = {cid: dist for cid, dist in crystal_hits}
        crystal_entries = []
        for c in all_crystals:
            dist = crystal_dist_map.get(c.id, 2.0)
            semantic_score = max(0.0, 1.0 - dist / 2.0)
            crystal_entries.append(SamplerEntry(
                id=c.id,
                resonance=c.resonance,
                timestamp=c.formed_at,
                semantic_score=semantic_score,
            ))
        sampled_crystals = resonance_sample(
            crystal_entries, k=min(n // 2 + 1, len(crystal_entries)),
            temperature=temperature,
            half_life_days=half_life_days * 2,
        )
        self._layers.crystals = [crystal_map[e.id] for e in sampled_crystals if e.id in crystal_map]

        # --- Records ---
        record_hits = self._store.query_vector(
            agent_id=self._agent_id,
            query_text=self._intention,
            n_results=50,
        )
        all_records = self._store.get_all_records(self._agent_id)
        record_dist_map = {rid: dist for rid, dist in record_hits}
        record_entries = []
        for r in all_records:
            dist = record_dist_map.get(r.id, 2.0)
            semantic_score = max(0.0, 1.0 - dist / 2.0)
            record_entries.append(SamplerEntry(
                id=r.id,
                resonance=r.resonance,
                timestamp=r.timestamp,
                semantic_score=semantic_score,
            ))
        sampled_records = resonance_sample(
            record_entries, k=n,
            temperature=temperature,
            half_life_days=half_life_days,
        )
        record_map = {r.id: r for r in all_records}
        self._layers.records = [record_map[e.id] for e in sampled_records if e.id in record_map]

        return self._layers

    async def insight(self) -> str:
        """
        Ask the Scribe to decode all three layers against the intention.

        Sigils are unlocked — their hidden_essence revealed in context.
        Crystals and records provide texture and specificity.
        The result is a revelation that could not have been predicted.
        """
        if not self._layers:
            await self.receive()

        self._revelation = await asyncio.to_thread(
            self._scribe.reveal,
            intention=self._intention,
            emerged_records=self._layers.records,
            emerged_crystals=self._layers.crystals,
            emerged_sigils=self._layers.sigils,
            blueprint=self._blueprint,
        )
        return self._revelation

    async def _close(self) -> None:
        """Inscribe the revelation as wisdom. Trigger compression checks."""
        if self._revelation:
            wisdom = Record(
                agent_id=self._agent_id,
                content=self._revelation,
                record_type="wisdom",
                resonance=0.9,
            )
            wisdom.set_tags(["ritual_wisdom", "revelation"])
            self._store.insert_record(wisdom)

        new_crystals, new_sigils = await asyncio.to_thread(
            self._crystallizer.check_and_crystallize,
            agent_id=self._agent_id,
            blueprint=self._blueprint,
        )
        self._new_crystals = new_crystals
        self._new_sigils = new_sigils

    @property
    def new_crystals(self) -> list[Crystal]:
        return self._new_crystals

    @property
    def new_sigils(self) -> list[Sigil]:
        return self._new_sigils


class AkashicRecords:
    """The eternal archive — entry point for all agent memory operations."""

    def __init__(
        self,
        agent_id: str,
        anthropic_api_key: str,
        data_dir: str = ".akashic",
        model: str = "claude-sonnet-4-6",
        crystallization_threshold: int = 8,
        sigil_threshold: int = 5,
    ):
        self._agent_id = agent_id
        self._store = AkashicStore(data_dir=data_dir)
        self._scribe = Scribe(api_key=anthropic_api_key, model=model)
        self._crystallizer = Crystallizer(
            store=self._store,
            scribe=self._scribe,
            threshold=crystallization_threshold,
            sigil_threshold=sigil_threshold,
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
        bp = Blueprint(agent_id=self._agent_id, name=name, mission=mission)
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
        Passively triggers crystallization/transcendence if thresholds are met.
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
            layers = await session.receive(n=5, temperature=0.8)
            # layers.sigils — the encrypted marks
            # layers.crystals — compressed wisdom
            # layers.records — raw experiences
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

    async def get_crystals(self, include_transcended: bool = False) -> list[Crystal]:
        return await asyncio.to_thread(
            self._store.get_all_crystals, self._agent_id, include_transcended
        )

    async def get_sigils(self) -> list[Sigil]:
        return await asyncio.to_thread(
            self._store.get_all_sigils, self._agent_id
        )

    async def count(self) -> dict[str, int]:
        records = await self.get_records()
        crystals = await self.get_crystals()
        sigils = await self.get_sigils()
        return {
            "active_records": len(records),
            "active_crystals": len(crystals),
            "sigils": len(sigils),
            "total_crystallized": sum(c.source_count for c in crystals),
            "total_transcended": sum(s.total_records for s in sigils),
        }
