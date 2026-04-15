import { StatusCard } from "@/components/status-card";
import type { SystemStatus } from "@/lib/status";

type StatusCardsProps = {
  statuses: SystemStatus[];
};

export function StatusCards({ statuses }: StatusCardsProps) {
  return (
    <div className="status-grid">
      {statuses.map((status) => (
        <StatusCard key={status.label} status={status} />
      ))}
    </div>
  );
}
