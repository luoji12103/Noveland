import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AdminDescriptionList,
  AdminMetric,
  AdminNotice,
  AdminSection,
  AdminState,
  AdminTable,
} from "@/features/admin/admin-foundation";

describe("admin foundation components", () => {
  it("renders accessible notices and states", () => {
    render(
      <>
        <AdminNotice tone="error">Provider secret reference is missing.</AdminNotice>
        <AdminState title="No health checks">Run a smoke test to create health evidence.</AdminState>
      </>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Provider secret reference is missing.");
    expect(screen.getByRole("heading", { name: "No health checks" })).toBeInTheDocument();
    expect(screen.getByText("Run a smoke test to create health evidence.")).toBeInTheDocument();
  });

  it("renders sections, metrics, tables, and detail lists", () => {
    render(
      <AdminSection title="Provider evidence" description="Safe status only.">
        <div className="dashboard-grid">
          <AdminMetric label="Health" value="ok" detail="auth_ref resolved" tone="ok" />
        </div>
        <AdminTable
          caption="Provider checks"
          columns={[
            { key: "status", header: "Status", render: (row) => row.status },
            { key: "reason", header: "Reason", render: (row) => row.reason },
          ]}
          rows={[{ id: "check-1", status: "ok", reason: "fake provider" }]}
          getRowKey={(row) => row.id}
          emptyTitle="No checks"
          emptyMessage="No provider health checks have been recorded."
        />
        <AdminDescriptionList
          items={[
            { label: "Worldline", value: "primary" },
            { label: "Visibility", value: "world_admin" },
          ]}
        />
      </AdminSection>,
    );

    expect(screen.getByRole("heading", { name: "Provider evidence" })).toBeInTheDocument();
    expect(screen.getByText("Safe status only.")).toBeInTheDocument();
    expect(screen.getByText("auth_ref resolved")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Provider checks" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeInTheDocument();
    expect(screen.getByText("primary")).toBeInTheDocument();
  });

  it("uses an empty state instead of an empty table body", () => {
    render(
      <AdminTable
        caption="Media jobs"
        columns={[{ key: "status", header: "Status", render: (row: { status: string }) => row.status }]}
        rows={[]}
        getRowKey={(row) => row.status}
        emptyTitle="No media jobs"
        emptyMessage="Queued jobs will appear here after an explicit admin action."
      />,
    );

    expect(screen.queryByRole("table", { name: "Media jobs" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No media jobs" })).toBeInTheDocument();
    expect(
      screen.getByText("Queued jobs will appear here after an explicit admin action."),
    ).toBeInTheDocument();
  });
});
