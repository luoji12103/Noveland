import { redirect } from "next/navigation";

import { ProviderAdmin } from "@/features/admin/provider-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getProviderAdminData } from "@/lib/worlds/server";

export default async function ProviderAdminPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  if (!subject.roles.includes("platform_admin")) {
    return (
      <WorkspaceShell
        subject={subject}
        title="Providers"
        intro="Provider profile management is available to platform administrators."
      >
        <section className="management-section">
          <p className="management-notice">Forbidden</p>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getProviderAdminData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Providers"
      intro="Manage non-secret provider profiles. API keys stay in runtime environment settings."
    >
      <ProviderAdmin data={data} />
    </WorkspaceShell>
  );
}
