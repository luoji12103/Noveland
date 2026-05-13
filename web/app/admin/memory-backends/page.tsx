import { redirect } from "next/navigation";

import { AdminNotice } from "@/features/admin/admin-foundation";
import { requirePlatformAdmin } from "@/features/admin/admin-route-guard";
import { MemoryBackendAdmin } from "@/features/admin/memory-backend-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getMemoryBackendAdminData } from "@/lib/worlds/server";

export default async function MemoryBackendAdminPage() {
  const subject = await getCurrentSubject();
  const guard = requirePlatformAdmin(subject, "Memory backend profile management");
  if (guard.status === "redirect") {
    redirect(guard.href);
  }
  if (guard.status === "forbidden") {
    return (
      <WorkspaceShell
        subject={guard.subject}
        title="Memory backends"
        intro="Memory backend profile management is available to platform administrators."
      >
        <section className="management-section">
          <AdminNotice tone="error">{guard.message}</AdminNotice>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getMemoryBackendAdminData();

  return (
    <WorkspaceShell
      subject={guard.subject}
      title="Memory backends"
      intro="Manage non-secret memory backend profiles used by world long-term memory."
    >
      <MemoryBackendAdmin data={data} />
    </WorkspaceShell>
  );
}
