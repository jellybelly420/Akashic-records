"""
Dual-layer storage: ChromaDB (vector field) + SQLite (structural records).
The etheric field for resonance retrieval, the physical plane for metadata.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import chromadb
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine, select

from .models import Blueprint, Crystal, Record, Sigil


class AkashicStore:
    def __init__(self, data_dir: str = ".akashic"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

        # SQLite — structural plane
        db_path = self._dir / "records.db"
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        # expire_on_commit=False keeps attribute values accessible after session closes
        self._Session = sessionmaker(
            bind=self._engine, class_=Session, expire_on_commit=False
        )
        SQLModel.metadata.create_all(self._engine)

        # ChromaDB — etheric (vector) plane
        self._chroma = chromadb.PersistentClient(path=str(self._dir / "chroma"))
        self._records_col = self._chroma.get_or_create_collection("records")
        self._crystals_col = self._chroma.get_or_create_collection("crystals")
        self._sigils_col = self._chroma.get_or_create_collection("sigils")

    # ------------------------------------------------------------------ #
    # Blueprint                                                            #
    # ------------------------------------------------------------------ #

    def save_blueprint(self, bp: Blueprint) -> None:
        with self._Session() as session:
            existing = session.get(Blueprint, bp.agent_id)
            if existing:
                existing.name = bp.name
                existing.mission = bp.mission
                existing.values = bp.values
                session.add(existing)
            else:
                session.add(bp)
            session.commit()

    def load_blueprint(self, agent_id: str) -> Optional[Blueprint]:
        with self._Session() as session:
            return session.get(Blueprint, agent_id)

    # ------------------------------------------------------------------ #
    # Records                                                              #
    # ------------------------------------------------------------------ #

    def insert_record(self, record: Record) -> None:
        with self._Session() as session:
            session.add(record)
            session.commit()

        # Index into vector field using content as document
        self._records_col.add(
            ids=[record.id],
            documents=[record.content],
            metadatas=[{
                "agent_id": record.agent_id,
                "record_type": record.record_type,
                "resonance": record.resonance,
                "tags": record.tags,
                "timestamp": record.timestamp.isoformat(),
                "absorbed": str(record.absorbed),
            }],
        )

    def get_all_records(self, agent_id: str, include_absorbed: bool = False) -> list[Record]:
        with self._Session() as session:
            stmt = select(Record).where(Record.agent_id == agent_id)
            if not include_absorbed:
                stmt = stmt.where(Record.absorbed == False)
            return list(session.exec(stmt).all())

    def get_record(self, record_id: str) -> Optional[Record]:
        with self._Session() as session:
            return session.get(Record, record_id)

    def mark_absorbed(self, record_ids: list[str]) -> None:
        with self._Session() as session:
            for rid in record_ids:
                r = session.get(Record, rid)
                if r:
                    r.absorbed = True
                    session.add(r)
            session.commit()

        # Remove from vector field — absorbed into the crystal
        if record_ids:
            self._records_col.delete(ids=record_ids)

    def query_vector(
        self,
        agent_id: str,
        query_text: str,
        n_results: int = 30,
    ) -> list[tuple[str, float]]:
        """Return (record_id, distance) pairs ordered by semantic proximity."""
        try:
            total = self._records_col.count()
            if total == 0:
                return []
            n = min(n_results, total)
            results = self._records_col.query(
                query_texts=[query_text],
                n_results=n,
                where={"agent_id": agent_id},
            )
            ids = results["ids"][0]
            distances = results["distances"][0]
            return list(zip(ids, distances))
        except Exception:
            return []

    def count_active_records(self, agent_id: str) -> int:
        with self._Session() as session:
            stmt = select(Record).where(
                Record.agent_id == agent_id,
                Record.absorbed == False,
            )
            return len(list(session.exec(stmt).all()))

    # ------------------------------------------------------------------ #
    # Crystals                                                             #
    # ------------------------------------------------------------------ #

    def insert_crystal(self, crystal: Crystal) -> None:
        with self._Session() as session:
            session.add(crystal)
            session.commit()

        self._crystals_col.add(
            ids=[crystal.id],
            documents=[crystal.essence],
            metadatas=[{
                "agent_id": crystal.agent_id,
                "symbol": crystal.symbol,
                "resonance": crystal.resonance,
                "source_count": crystal.source_count,
                "tags": crystal.tags,
            }],
        )

    def get_all_crystals(self, agent_id: str, include_transcended: bool = False) -> list[Crystal]:
        with self._Session() as session:
            stmt = select(Crystal).where(Crystal.agent_id == agent_id)
            if not include_transcended:
                stmt = stmt.where(Crystal.transcended == False)
            return list(session.exec(stmt).all())

    def mark_crystals_transcended(self, crystal_ids: list[str]) -> None:
        with self._Session() as session:
            for cid in crystal_ids:
                c = session.get(Crystal, cid)
                if c:
                    c.transcended = True
                    session.add(c)
            session.commit()
        if crystal_ids:
            self._crystals_col.delete(ids=crystal_ids)

    def query_crystals_vector(
        self,
        agent_id: str,
        query_text: str,
        n_results: int = 10,
    ) -> list[tuple[str, float]]:
        try:
            total = self._crystals_col.count()
            if total == 0:
                return []
            n = min(n_results, total)
            results = self._crystals_col.query(
                query_texts=[query_text],
                n_results=n,
                where={"agent_id": agent_id},
            )
            ids = results["ids"][0]
            distances = results["distances"][0]
            return list(zip(ids, distances))
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Sigils                                                               #
    # ------------------------------------------------------------------ #

    def insert_sigil(self, sigil: Sigil) -> None:
        with self._Session() as session:
            session.add(sigil)
            session.commit()

        # Index sigil by its name (the "door") — the glyph is too short to embed
        self._sigils_col.add(
            ids=[sigil.id],
            documents=[f"{sigil.glyph} {sigil.name}"],
            metadatas=[{
                "agent_id": sigil.agent_id,
                "glyph": sigil.glyph,
                "name": sigil.name,
                "resonance": sigil.resonance,
                "crystal_count": sigil.crystal_count,
                "total_records": sigil.total_records,
                "tags": sigil.tags,
            }],
        )

    def get_all_sigils(self, agent_id: str) -> list[Sigil]:
        with self._Session() as session:
            stmt = select(Sigil).where(Sigil.agent_id == agent_id)
            return list(session.exec(stmt).all())

    def query_sigils_vector(
        self,
        agent_id: str,
        query_text: str,
        n_results: int = 5,
    ) -> list[tuple[str, float]]:
        try:
            total = self._sigils_col.count()
            if total == 0:
                return []
            n = min(n_results, total)
            results = self._sigils_col.query(
                query_texts=[query_text],
                n_results=n,
                where={"agent_id": agent_id},
            )
            ids = results["ids"][0]
            distances = results["distances"][0]
            return list(zip(ids, distances))
        except Exception:
            return []

    def count_active_crystals(self, agent_id: str) -> int:
        with self._Session() as session:
            stmt = select(Crystal).where(
                Crystal.agent_id == agent_id,
                Crystal.transcended == False,
            )
            return len(list(session.exec(stmt).all()))
