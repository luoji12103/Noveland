"use client";

import type { WorldlineBrowserData } from "@/lib/worlds/server";
import type { Worldline } from "@/lib/worlds/types";

type WorldlineBrowserProps = {
  data: WorldlineBrowserData;
};

export function WorldlineBrowser({ data }: WorldlineBrowserProps) {
  if (data.selectedWorld === null) {
    return (
      <section className="management-section">
        <p className="management-notice" data-tone="error">
          {data.loadError ?? "Worldlines are unavailable."}
        </p>
      </section>
    );
  }

  const baseWorldline = data.worldlines.find((worldline) => worldline.id === data.baseWorldlineId) ?? null;
  const compareWorldline =
    data.worldlines.find((worldline) => worldline.id === data.compareWorldlineId) ?? null;
  const rootCount = data.worldlines.filter((worldline) => worldline.parent_worldline_id === null).length;
  const forkCount = data.worldlines.length - rootCount;

  return (
    <section className="management-section worldline-browser">
      <section className="management-panel worldline-summary" aria-labelledby="worldline-summary-title">
        <div>
          <h2 className="section-title" id="worldline-summary-title">
            Worldline browser
          </h2>
          <p className="admin-section-copy">
            {data.selectedWorld.name}: read-only branch inventory and safe comparison summaries.
          </p>
        </div>
        <div className="worldline-metrics" aria-label="Worldline counts">
          <span>{data.worldlines.length} branches</span>
          <span>{rootCount} root</span>
          <span>{forkCount} forks</span>
        </div>
      </section>

      <div className="worldline-browser-grid">
        <section className="management-panel" aria-labelledby="worldline-tree-title">
          <h2 className="section-title" id="worldline-tree-title">
            Branches
          </h2>
          {data.worldlines.length === 0 ? (
            <p className="management-notice">No worldlines are available.</p>
          ) : (
            <ol className="worldline-list">
              {orderedWorldlines(data.worldlines).map((worldline) => (
                <li
                  className="worldline-list-item"
                  data-selected={
                    worldline.id === data.baseWorldlineId || worldline.id === data.compareWorldlineId
                  }
                  key={worldline.id}
                >
                  <div>
                    <h3>{worldline.name}</h3>
                    <p>
                      {worldline.worldline_key} - {worldline.status}
                    </p>
                  </div>
                  <dl>
                    <div>
                      <dt>Parent</dt>
                      <dd>{parentLabel(data.worldlines, worldline)}</dd>
                    </div>
                    <div>
                      <dt>Fork sequence</dt>
                      <dd>{worldline.fork_event_sequence ?? "None"}</dd>
                    </div>
                    <div>
                      <dt>Updated</dt>
                      <dd>
                        <time dateTime={worldline.updated_at}>{formatDate(worldline.updated_at)}</time>
                      </dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="management-panel" aria-labelledby="worldline-compare-title">
          <h2 className="section-title" id="worldline-compare-title">
            Compare branches
          </h2>
          <form className="worldline-compare-form" method="get">
            <label>
              Base
              <select className="text-input" name="base" defaultValue={data.baseWorldlineId ?? ""}>
                {data.worldlines.map((worldline) => (
                  <option key={worldline.id} value={worldline.id}>
                    {worldline.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Compare
              <select className="text-input" name="compare" defaultValue={data.compareWorldlineId ?? ""}>
                {data.worldlines.map((worldline) => (
                  <option key={worldline.id} value={worldline.id}>
                    {worldline.name}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-button" disabled={data.worldlines.length === 0} type="submit">
              Compare worldlines
            </button>
          </form>

          {data.comparisonError !== null ? (
            <p className="management-notice" data-tone="warning">
              {data.comparisonError}
            </p>
          ) : null}

          {data.comparison === null ? (
            <p className="management-notice">Select two branches to compare safe summaries.</p>
          ) : (
            <article className="worldline-comparison" aria-label="Worldline comparison summary">
              <h3>
                {baseWorldline?.name ?? "Base"} to {compareWorldline?.name ?? "Compare"}
              </h3>
              <div className="worldline-comparison-grid">
                <Metric label="Divergent events" value={data.comparison.divergent_event_count} />
                <Metric label="Relationship deltas" value={data.comparison.relationship_delta_count} />
                <Metric label="Faction deltas" value={data.comparison.faction_delta_count} />
                <Metric label="Choice deltas" value={data.comparison.choice_delta_count} />
                <Metric label="Fork sequence" value={data.comparison.fork_event_sequence ?? "None"} />
              </div>
              <p className="admin-section-copy">
                Comparison output is aggregate only. Rollback, merge, and branch switching are unavailable here.
              </p>
            </article>
          )}
        </section>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="worldline-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function orderedWorldlines(worldlines: Worldline[]): Worldline[] {
  return [...worldlines].sort((left, right) => {
    if (left.parent_worldline_id === null && right.parent_worldline_id !== null) {
      return -1;
    }
    if (left.parent_worldline_id !== null && right.parent_worldline_id === null) {
      return 1;
    }
    return left.created_at.localeCompare(right.created_at);
  });
}

function parentLabel(worldlines: Worldline[], worldline: Worldline): string {
  if (worldline.parent_worldline_id === null) {
    return "Root";
  }
  return worldlines.find((item) => item.id === worldline.parent_worldline_id)?.name ?? "Unknown";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
