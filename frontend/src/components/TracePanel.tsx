import type { ReactElement } from "react";
import type { TraceEntry } from "../api/types";

export function TracePanel({ entries }: { entries: TraceEntry[] }): ReactElement {
  return (
    <section className="trace-panel">
      <h2>Computer-use trace</h2>
      {entries.length === 0 ? <p>No computer-use actions yet.</p> : null}
      {entries.map((entry) => (
        <div className="trace-row" key={entry.trace_id}>
          <span>{entry.action?.type ?? "observation"}</span>
          <strong>{entry.verification.status}</strong>
          <p>{entry.verification.message}</p>
        </div>
      ))}
    </section>
  );
}
