import { redirect } from "next/navigation";

import { WorldOverview } from "@/features/worlds/world-overview";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getWorldWorkspaceData } from "@/lib/worlds/server";

type WorldPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldPage({ params }: WorldPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getWorldWorkspaceData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title={data.selectedWorld?.name ?? "World workspace"}
      intro="Manage world state, scenes, memberships, clock, schedules, diagnostics, replay, and snapshots."
      worldId={worldId}
    >
      <WorldOverview data={data} />
    </WorkspaceShell>
  );
}
