export type StatusTone = "ready" | "local" | "waiting";

export type SystemStatus = {
  label: string;
  value: string;
  detail: string;
  tone: StatusTone;
};

export const systemStatuses: SystemStatus[] = [
  {
    label: "API",
    value: "Health endpoint ready",
    detail: "GET /health returns the fixed v0.1.0 contract.",
    tone: "ready",
  },
  {
    label: "Runtime",
    value: "Finite tick ready",
    detail: "The worker advances running clocks once and broadcasts world events.",
    tone: "ready",
  },
  {
    label: "Storage",
    value: "Local services defined",
    detail: "PostgreSQL, pgvector, JetStream, and local object storage paths are configured.",
    tone: "local",
  },
  {
    label: "Worlds",
    value: "Management console ready",
    detail: "Worlds, clocks, replay state, and snapshots are available to authorized users.",
    tone: "ready",
  },
];
