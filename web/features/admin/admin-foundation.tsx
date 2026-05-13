import type { ReactNode } from "react";

export type AdminNoticeTone = "info" | "success" | "warning" | "error";

type AdminNoticeProps = {
  children: ReactNode;
  tone?: AdminNoticeTone;
};

export function AdminNotice({ children, tone = "info" }: AdminNoticeProps) {
  return (
    <p className="management-notice" data-tone={tone} role={tone === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

type AdminStateProps = {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  tone?: "empty" | "loading" | "error";
};

export function AdminState({ title, children, action, tone = "empty" }: AdminStateProps) {
  return (
    <article className="admin-state" data-tone={tone}>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
      {action === undefined ? null : <div className="admin-state-action">{action}</div>}
    </article>
  );
}

type AdminSectionProps = {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
};

export function AdminSection({ title, description, children, actions }: AdminSectionProps) {
  const titleId = `${slugify(title)}-title`;
  return (
    <section className="management-panel" aria-labelledby={titleId}>
      <div className="admin-section-header">
        <div>
          <h2 className="section-title" id={titleId}>
            {title}
          </h2>
          {description === undefined ? null : <p className="admin-section-copy">{description}</p>}
        </div>
        {actions === undefined ? null : <div className="button-row">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

type AdminMetricProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "ok" | "warning" | "error";
};

export function AdminMetric({ label, value, detail, tone = "neutral" }: AdminMetricProps) {
  return (
    <div className="metric" data-tone={tone}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      {detail === undefined ? null : <p className="status-detail">{detail}</p>}
    </div>
  );
}

type AdminTableColumn<Row> = {
  key: string;
  header: string;
  render: (row: Row) => ReactNode;
};

type AdminTableProps<Row> = {
  caption: string;
  columns: AdminTableColumn<Row>[];
  rows: Row[];
  getRowKey: (row: Row) => string;
  emptyTitle: string;
  emptyMessage: string;
};

export function AdminTable<Row>({
  caption,
  columns,
  rows,
  getRowKey,
  emptyTitle,
  emptyMessage,
}: AdminTableProps<Row>) {
  if (rows.length === 0) {
    return <AdminState title={emptyTitle}>{emptyMessage}</AdminState>;
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type AdminDescriptionListProps = {
  items: Array<{
    label: string;
    value: ReactNode;
  }>;
};

export function AdminDescriptionList({ items }: AdminDescriptionListProps) {
  return (
    <dl className="admin-description-list">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

type AdminActionBarProps = {
  children: ReactNode;
};

export function AdminActionBar({ children }: AdminActionBarProps) {
  return <div className="admin-action-bar">{children}</div>;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
