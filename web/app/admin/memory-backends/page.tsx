import { redirect } from "next/navigation";

import { MemoryBackendAdmin } from "@/features/admin/memory-backend-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getMemoryBackendAdminData } from "@/lib/worlds/server";

export default async function MemoryBackendAdminPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  if (!subject.roles.includes("platform_admin")) {
    return (
      <WorkspaceShell
        subject={subject}
        title="Memory backends"
        intro="Memory backend profile management is available to platform administrators."
      >
        <section className="management-section">
          <p className="management-notice">Forbidden</p>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getMemoryBackendAdminData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Memory backends"
      intro="Manage non-secret memory backend profiles used by world long-term memory."
    >
      <MemoryBackendAdmin data={data} />
    </WorkspaceShell>
  );
}
