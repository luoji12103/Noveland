import { redirect } from "next/navigation";

import { NarrativeWorkspace } from "@/features/worlds/narrative-workspace";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getNarrativeWorkspaceData } from "@/lib/worlds/server";

type NarrativePageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function NarrativePage({ params }: NarrativePageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getNarrativeWorkspaceData(worldId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Narrative"
      intro="Review and create narrative artifacts produced by agents or operator curation."
      worldId={worldId}
    >
      <NarrativeWorkspace worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
