import { redirect } from "next/navigation";

import { AdminNotice } from "@/features/admin/admin-foundation";
import { requirePlatformAdmin } from "@/features/admin/admin-route-guard";
import { PresetAdmin } from "@/features/admin/preset-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getPresetAdminData } from "@/lib/worlds/server";

export default async function PresetAdminPage() {
  const subject = await getCurrentSubject();
  const guard = requirePlatformAdmin(subject, "Preset management");
  if (guard.status === "redirect") {
    redirect(guard.href);
  }
  if (guard.status === "forbidden") {
    return (
      <WorkspaceShell
        subject={guard.subject}
        title="Presets"
        intro="Preset management is available to platform administrators."
      >
        <section className="management-section">
          <AdminNotice tone="error">{guard.message}</AdminNotice>
        </section>
      </WorkspaceShell>
    );
  }

  const data = await getPresetAdminData();

  return (
    <WorkspaceShell
      subject={guard.subject}
      title="Presets"
      intro="Manage platform-level agent presets used by builders and world composition imports."
    >
      <PresetAdmin presets={data.presets} loadError={data.loadError} />
    </WorkspaceShell>
  );
}
