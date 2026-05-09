import type { ReactElement } from "react";
import type { TraceEntry } from "../api/types";

export function TracePanel({ entries }: { entries: TraceEntry[] }): ReactElement {
  return (
    <section className="trace-panel">
      <h2>Harness + computer-use trace</h2>
      {entries.length === 0 ? <p>No harness or computer-use events yet.</p> : null}
      {entries.map((entry) => (
        <div className="trace-row" key={entry.trace_id}>
          <span>{entry.harness?.phase ?? entry.action?.type ?? "observation"}</span>
          <strong>{entry.verification.status}</strong>
          <p>{entry.verification.message}</p>
          {entry.harness !== null && entry.harness !== undefined ? (
            <div className="trace-detail">
              <small>
                {entry.harness.provider}/{entry.harness.model}
              </small>
              <p>{entry.harness.message}</p>
              {entry.harness.goal !== null ? <p>Goal: {entry.harness.goal}</p> : null}
              {entry.harness.raw_output_text !== null ? (
                <pre>{entry.harness.raw_output_text}</pre>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}
    </section>
  );
}
