import Image from "next/image";

import { StatusCards } from "@/features/dashboard/status-cards";
import { systemStatuses } from "@/lib/status";

const metrics = [
  { label: "Worlds", value: "0 configured" },
  { label: "Agents", value: "0 active" },
  { label: "Narrative", value: "Not scheduled" },
];

export default function Home() {
  return (
    <main className="page-shell">
      <section className="top-band">
        <div className="top-band-inner">
          <div>
            <p className="eyebrow">Noveland control surface</p>
            <h1 className="title">World kernel standing by</h1>
            <p className="intro">
              Create the first world after the core schema, access checks, clock state, and plugin
              registry tasks land.
            </p>
          </div>
          <Image
            className="world-image"
            src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80"
            width={1200}
            height={800}
            priority
            alt="Mountain lake at sunrise"
          />
        </div>
      </section>

      <section className="dashboard-grid" aria-label="World overview">
        {metrics.map((metric) => (
          <div className="metric" key={metric.label}>
            <p className="metric-label">{metric.label}</p>
            <p className="metric-value">{metric.value}</p>
          </div>
        ))}
      </section>

      <section className="status-section">
        <h2 className="section-title">System status</h2>
        <StatusCards statuses={systemStatuses} />
      </section>
    </main>
  );
}
