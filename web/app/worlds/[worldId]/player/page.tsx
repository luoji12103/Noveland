import { redirect } from "next/navigation";

import { PlayerInteractions } from "@/features/worlds/player-interactions";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getPlayerInteractionData } from "@/lib/worlds/server";

type PlayerPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function PlayerPage({ params }: PlayerPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getPlayerInteractionData(worldId, subject.user_id);

  return (
    <WorkspaceShell
      subject={subject}
      title="Player"
      intro="Review choices, journal entries, notifications, and interventions for the active worldline."
      worldId={worldId}
    >
      <PlayerInteractions worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
