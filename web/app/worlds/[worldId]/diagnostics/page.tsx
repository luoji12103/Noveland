import { redirect } from "next/navigation";

import { MultimodalDiagnosticsAdmin } from "@/features/admin/multimodal-diagnostics-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getMultimodalDiagnosticsAdminData } from "@/lib/worlds/server";

type WorldDiagnosticsPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldDiagnosticsPage({ params }: WorldDiagnosticsPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getMultimodalDiagnosticsAdminData(
    worldId,
    subject.roles.includes("platform_admin"),
  );

  return (
    <WorkspaceShell
      subject={subject}
      title="Diagnostics"
      intro="Review multimodal blockers, leak checks, provider health evidence, media integrity, and eval runs."
      worldId={worldId}
    >
      <MultimodalDiagnosticsAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
