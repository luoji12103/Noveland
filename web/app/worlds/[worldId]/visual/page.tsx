import { redirect } from "next/navigation";

import { VisualAdmin } from "@/features/admin/visual-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getVisualAdminData } from "@/lib/worlds/server";

type WorldVisualPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldVisualPage({ params }: WorldVisualPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getVisualAdminData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title="Visual"
      intro="Manage strict-worldline sprite sets, expression variants, backgrounds, resolver previews, and explicit scene composition."
      worldId={worldId}
    >
      <VisualAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
