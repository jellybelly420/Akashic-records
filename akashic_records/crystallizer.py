"""
The Crystallizer — watches the field and triggers crystallization events.

When records of the same thematic cluster accumulate beyond a threshold,
a spontaneous crystallization occurs: many become one, compressed wisdom.
The agent does not initiate this — it just happens, like sediment becoming stone.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .models import Blueprint, Crystal, Record
from .scribe import Scribe
from .store import AkashicStore


class Crystallizer:
    def __init__(
        self,
        store: AkashicStore,
        scribe: Scribe,
        threshold: int = 8,
    ):
        self._store = store
        self._scribe = scribe
        self._threshold = threshold

    def check_and_crystallize(
        self,
        agent_id: str,
        blueprint: Optional[Blueprint] = None,
    ) -> list[Crystal]:
        """
        Inspect active records. If any thematic cluster exceeds the threshold,
        crystallize it. Returns newly formed crystals.
        """
        records = self._store.get_all_records(agent_id, include_absorbed=False)
        if len(records) < self._threshold:
            return []

        clusters = self._cluster_by_tags(records)
        formed: list[Crystal] = []

        for tag, cluster_records in clusters.items():
            if len(cluster_records) >= self._threshold:
                crystal = self._form_crystal(
                    agent_id=agent_id,
                    records=cluster_records,
                    dominant_tag=tag,
                    blueprint=blueprint,
                )
                formed.append(crystal)

        # If no tag cluster is large enough but total records exceed threshold * 2,
        # crystallize the oldest batch regardless of tag
        if not formed and len(records) >= self._threshold * 2:
            oldest = sorted(records, key=lambda r: r.timestamp)[: self._threshold]
            crystal = self._form_crystal(
                agent_id=agent_id,
                records=oldest,
                dominant_tag="miscellaneous",
                blueprint=blueprint,
            )
            formed.append(crystal)

        return formed

    def _cluster_by_tags(self, records: list[Record]) -> dict[str, list[Record]]:
        """Group records by their most prominent tag."""
        tag_map: dict[str, list[Record]] = defaultdict(list)
        for record in records:
            tags = record.get_tags()
            if tags:
                tag_map[tags[0]].append(record)
            else:
                tag_map["untagged"].append(record)
        return dict(tag_map)

    def _form_crystal(
        self,
        agent_id: str,
        records: list[Record],
        dominant_tag: str,
        blueprint: Optional[Blueprint],
    ) -> Crystal:
        """Ask Claude to compress records into a crystal, then store it."""
        essence, symbol = self._scribe.crystallize(records, blueprint)

        # Average resonance of source records, boosted slightly
        avg_resonance = sum(r.resonance for r in records) / len(records)
        crystal_resonance = min(1.0, avg_resonance * 1.2)

        # Collect all unique tags
        all_tags: set[str] = set()
        for r in records:
            all_tags.update(r.get_tags())

        crystal = Crystal(
            agent_id=agent_id,
            essence=essence,
            symbol=symbol,
            resonance=crystal_resonance,
            source_count=len(records),
        )
        crystal.set_tags(sorted(all_tags))

        # Persist crystal
        self._store.insert_crystal(crystal)

        # Mark source records as absorbed
        self._store.mark_absorbed([r.id for r in records])

        return crystal
