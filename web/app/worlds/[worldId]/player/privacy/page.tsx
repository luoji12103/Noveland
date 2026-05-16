import { redirect } from "next/navigation";

import { PlayerPrivacyControls } from "@/features/worlds/player-privacy-controls";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getPlayerPrivacyData } from "@/lib/worlds/server";

type PlayerPrivacyPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function PlayerPrivacyPage({ params }: PlayerPrivacyPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getPlayerPrivacyData(worldId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Player privacy"
      intro="Export player records and track deletion review requests without changing shared world history."
      worldId={worldId}
    >
      <PlayerPrivacyControls worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
