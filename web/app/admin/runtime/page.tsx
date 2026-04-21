import { redirect } from "next/navigation";

import { RuntimeAdmin } from "@/features/admin/runtime-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getRuntimeAdminData } from "@/lib/worlds/server";

export default async function RuntimeAdminPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  if (!subject.roles.includes("platform_admin")) {
    return (
      <WorkspaceShell
        subject={subject}
        title="Runtime"
        intro="Runtime control is available to platform administrators."
      >
        <section className="management-section">
          <p className="management-notice">Forbidden</p>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getRuntimeAdminData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Runtime"
      intro="Start or stop desired runtime processing and inspect recent diagnostics."
    >
      <RuntimeAdmin data={data} />
    </WorkspaceShell>
  );
}
