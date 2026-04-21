"""
The Crystallizer — watches the field and triggers compression events.

Two tiers of spontaneous compression:
  Tier 1: Records → Crystal  (when record cluster exceeds threshold)
  Tier 2: Crystals → Sigil   (when crystal cluster exceeds sigil_threshold)

Neither is triggered by the agent — they emerge from accumulated weight.
The agent does not call crystallize(); it just happens, like sediment becoming stone,
and stone becoming a single mark carved into the wall of time.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .models import Blueprint, Crystal, Record, Sigil
from .scribe import Scribe
from .store import AkashicStore


class Crystallizer:
    def __init__(
        self,
        store: AkashicStore,
        scribe: Scribe,
        threshold: int = 8,
        sigil_threshold: int = 5,
    ):
        self._store = store
        self._scribe = scribe
        self._threshold = threshold
        self._sigil_threshold = sigil_threshold

    def check_and_crystallize(
        self,
        agent_id: str,
        blueprint: Optional[Blueprint] = None,
    ) -> tuple[list[Crystal], list[Sigil]]:
        """
        Inspect active records and crystals.
        Trigger crystallization and/or transcendence if thresholds are exceeded.
        Returns (new_crystals, new_sigils).
        """
        new_crystals = self._check_records(agent_id, blueprint)
        new_sigils = self._check_crystals(agent_id, blueprint)
        return new_crystals, new_sigils

    # ------------------------------------------------------------------ #
    # Tier 1: Records → Crystals                                           #
    # ------------------------------------------------------------------ #

    def _check_records(
        self,
        agent_id: str,
        blueprint: Optional[Blueprint],
    ) -> list[Crystal]:
        records = self._store.get_all_records(agent_id, include_absorbed=False)
        if len(records) < self._threshold:
            return []

        clusters = self._cluster_records_by_tags(records)
        formed: list[Crystal] = []

        for tag, cluster_records in clusters.items():
            if len(cluster_records) >= self._threshold:
                crystal = self._form_crystal(agent_id, cluster_records, tag, blueprint)
                formed.append(crystal)

        # If no tag cluster qualifies but total is very large, crystallize oldest batch
        if not formed and len(records) >= self._threshold * 2:
            oldest = sorted(records, key=lambda r: r.timestamp)[: self._threshold]
            crystal = self._form_crystal(agent_id, oldest, "miscellaneous", blueprint)
            formed.append(crystal)

        return formed

    def _cluster_records_by_tags(self, records: list[Record]) -> dict[str, list[Record]]:
        tag_map: dict[str, list[Record]] = defaultdict(list)
        for record in records:
            tags = record.get_tags()
            tag_map[tags[0] if tags else "untagged"].append(record)
        return dict(tag_map)

    def _form_crystal(
        self,
        agent_id: str,
        records: list[Record],
        dominant_tag: str,
        blueprint: Optional[Blueprint],
    ) -> Crystal:
        essence, symbol = self._scribe.crystallize(records, blueprint)

        avg_resonance = sum(r.resonance for r in records) / len(records)

        all_tags: set[str] = set()
        for r in records:
            all_tags.update(r.get_tags())

        crystal = Crystal(
            agent_id=agent_id,
            essence=essence,
            symbol=symbol,
            resonance=min(1.0, avg_resonance * 1.2),
            source_count=len(records),
        )
        crystal.set_tags(sorted(all_tags))

        self._store.insert_crystal(crystal)
        self._store.mark_absorbed([r.id for r in records])

        return crystal

    # ------------------------------------------------------------------ #
    # Tier 2: Crystals → Sigils                                            #
    # ------------------------------------------------------------------ #

    def _check_crystals(
        self,
        agent_id: str,
        blueprint: Optional[Blueprint],
    ) -> list[Sigil]:
        crystals = self._store.get_all_crystals(agent_id, include_transcended=False)
        if len(crystals) < self._sigil_threshold:
            return []

        clusters = self._cluster_crystals_by_tags(crystals)
        formed: list[Sigil] = []

        # Get existing sigil glyphs to avoid duplication
        existing_sigils = self._store.get_all_sigils(agent_id)
        existing_glyphs = {s.glyph for s in existing_sigils}

        for tag, cluster_crystals in clusters.items():
            if len(cluster_crystals) >= self._sigil_threshold:
                sigil = self._form_sigil(
                    agent_id, cluster_crystals, existing_glyphs, blueprint
                )
                existing_glyphs.add(sigil.glyph)
                formed.append(sigil)

        # Overflow: if total non-transcended crystals >> threshold, compress oldest
        if not formed and len(crystals) >= self._sigil_threshold * 2:
            oldest = sorted(crystals, key=lambda c: c.formed_at)[: self._sigil_threshold]
            sigil = self._form_sigil(agent_id, oldest, existing_glyphs, blueprint)
            formed.append(sigil)

        return formed

    def _cluster_crystals_by_tags(self, crystals: list[Crystal]) -> dict[str, list[Crystal]]:
        tag_map: dict[str, list[Crystal]] = defaultdict(list)
        for crystal in crystals:
            tags = crystal.get_tags()
            tag_map[tags[0] if tags else "untagged"].append(crystal)
        return dict(tag_map)

    def _form_sigil(
        self,
        agent_id: str,
        crystals: list[Crystal],
        existing_glyphs: set[str],
        blueprint: Optional[Blueprint],
    ) -> Sigil:
        glyph, name, hidden_essence = self._scribe.transcend(
            crystals, existing_glyphs, blueprint
        )

        total_records = sum(c.source_count for c in crystals)
        avg_resonance = sum(c.resonance for c in crystals) / len(crystals)

        all_tags: set[str] = set()
        for c in crystals:
            all_tags.update(c.get_tags())

        sigil = Sigil(
            agent_id=agent_id,
            glyph=glyph,
            name=name,
            hidden_essence=hidden_essence,
            resonance=min(1.0, avg_resonance * 1.15),
            crystal_count=len(crystals),
            total_records=total_records,
        )
        sigil.set_tags(sorted(all_tags))

        self._store.insert_sigil(sigil)
        self._store.mark_crystals_transcended([c.id for c in crystals])

        return sigil
