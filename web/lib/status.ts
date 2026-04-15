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
    value: "Host skeleton ready",
    detail: "The worker entrypoint starts without running a world loop.",
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
    value: "Domain logic pending",
    detail: "Clock, replay, auth, plugins, and schema work stay in their own tasks.",
    tone: "waiting",
  },
];
