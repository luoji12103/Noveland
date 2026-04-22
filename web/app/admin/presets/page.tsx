import { redirect } from "next/navigation";

import { PresetAdmin } from "@/features/admin/preset-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getPresetAdminData } from "@/lib/worlds/server";

export default async function PresetAdminPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  if (!subject.roles.includes("platform_admin")) {
    return (
      <WorkspaceShell
        subject={subject}
        title="Presets"
        intro="Preset management is available to platform administrators."
      >
        <section className="management-section">
          <p className="management-notice">Forbidden</p>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getPresetAdminData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Presets"
      intro="Manage platform-level agent presets used by builders and world composition imports."
    >
      <PresetAdmin presets={data.presets} loadError={data.loadError} />
    </WorkspaceShell>
  );
}
