import type { SystemStatus } from "@/lib/status";

type StatusCardProps = {
  status: SystemStatus;
};

export function StatusCard({ status }: StatusCardProps) {
  return (
    <article className="status-card" data-tone={status.tone}>
      <p className="status-label">{status.label}</p>
      <p className="status-value">{status.value}</p>
      <p className="status-detail">{status.detail}</p>
    </article>
  );
}
