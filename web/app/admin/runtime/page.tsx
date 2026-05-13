import { redirect } from "next/navigation";

import { AdminNotice } from "@/features/admin/admin-foundation";
import { requirePlatformAdmin } from "@/features/admin/admin-route-guard";
import { RuntimeAdmin } from "@/features/admin/runtime-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getRuntimeAdminData } from "@/lib/worlds/server";

export default async function RuntimeAdminPage() {
  const subject = await getCurrentSubject();
  const guard = requirePlatformAdmin(subject, "Runtime control");
  if (guard.status === "redirect") {
    redirect(guard.href);
  }
  if (guard.status === "forbidden") {
    return (
      <WorkspaceShell
        subject={guard.subject}
        title="Runtime"
        intro="Runtime control is available to platform administrators."
      >
        <section className="management-section">
          <AdminNotice tone="error">{guard.message}</AdminNotice>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getRuntimeAdminData();

  return (
    <WorkspaceShell
      subject={guard.subject}
      title="Runtime"
      intro="Start or stop desired runtime processing and inspect recent diagnostics."
    >
      <RuntimeAdmin data={data} />
    </WorkspaceShell>
  );
}
