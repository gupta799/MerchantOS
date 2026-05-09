from __future__ import annotations

import json
from pathlib import Path

from app.config import AppSettings
from app.ids import SessionId, new_trace_id
from app.models import (
    ActionVerification,
    BrowserObservation,
    ComputerAction,
    HarnessTrace,
    TraceEntry,
    TraceResponse,
    VerificationStatus,
    utc_now,
)
from app.services.telemetry_service import TelemetryService
from app.store import InMemoryStore


class TraceService:
    def __init__(self, store: InMemoryStore, settings: AppSettings | None = None) -> None:
        self._store = store
        self._telemetry = TelemetryService(store)
        self._telemetry_dir = self._resolve_telemetry_dir(settings)

    def record_observation(self, session_id: SessionId, observation: BrowserObservation) -> TraceEntry:
        entry = self._store.add_trace(
            TraceEntry(
                trace_id=new_trace_id(),
                session_id=session_id,
                observation=observation,
                verification=ActionVerification(
                    status=VerificationStatus.PENDING,
                    message="Browser observation captured",
                ),
            )
        )
        self._append_telemetry_snapshot(entry)
        return entry

    def record_action(
        self,
        session_id: SessionId,
        action: ComputerAction,
        observation: BrowserObservation,
        status: VerificationStatus,
        message: str,
    ) -> TraceEntry:
        entry = self._store.add_trace(
            TraceEntry(
                trace_id=new_trace_id(),
                session_id=session_id,
                action=action,
                observation=observation,
                verification=ActionVerification(status=status, message=message),
            )
        )
        self._append_telemetry_snapshot(entry)
        return entry

    def record_harness_trace(
        self,
        session_id: SessionId,
        harness: HarnessTrace,
        status: VerificationStatus,
        message: str,
    ) -> TraceEntry:
        entry = self._store.add_trace(
            TraceEntry(
                trace_id=new_trace_id(),
                session_id=session_id,
                harness=harness,
                verification=ActionVerification(status=status, message=message),
            )
        )
        self._append_telemetry_snapshot(entry)
        return entry

    def response(self, session_id: SessionId) -> TraceResponse:
        return TraceResponse(session_id=session_id, entries=self._store.traces_for_session(session_id))

    def _append_telemetry_snapshot(self, entry: TraceEntry) -> None:
        if self._telemetry_dir is None:
            return
        simulation_id = self._store.simulation_id_for_session(entry.session_id)
        if simulation_id is None:
            return
        report = self._telemetry.build_report(simulation_id, entry.session_id)
        payload = {
            "timestamp": utc_now().isoformat(),
            "session_id": entry.session_id,
            "simulation_id": simulation_id,
            "trace_id": entry.trace_id,
            "telemetry": report.model_dump(mode="json"),
        }
        self._telemetry_dir.mkdir(parents=True, exist_ok=True)
        path = self._telemetry_dir / f"{entry.session_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _resolve_telemetry_dir(self, settings: AppSettings | None) -> Path | None:
        if settings is None:
            return None
        telemetry_dir = settings.telemetry_output_dir.strip()
        if telemetry_dir == "":
            return None
        return Path(telemetry_dir)
