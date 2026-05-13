import { redirect } from "next/navigation";

import { AdminNotice } from "@/features/admin/admin-foundation";
import { requirePlatformAdmin } from "@/features/admin/admin-route-guard";
import { ProviderAdmin } from "@/features/admin/provider-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getProviderAdminData } from "@/lib/worlds/server";

export default async function ProviderAdminPage() {
  const subject = await getCurrentSubject();
  const guard = requirePlatformAdmin(subject, "Provider profile management");
  if (guard.status === "redirect") {
    redirect(guard.href);
  }
  if (guard.status === "forbidden") {
    return (
      <WorkspaceShell
        subject={guard.subject}
        title="Providers"
        intro="Provider profile management is available to platform administrators."
      >
        <section className="management-section">
          <AdminNotice tone="error">{guard.message}</AdminNotice>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getProviderAdminData();

  return (
    <WorkspaceShell
      subject={guard.subject}
      title="Providers"
      intro="Manage non-secret provider profiles. API keys stay in runtime environment settings."
    >
      <ProviderAdmin data={data} />
    </WorkspaceShell>
  );
}
