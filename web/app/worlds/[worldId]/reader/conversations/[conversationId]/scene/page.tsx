import { redirect } from "next/navigation";

import { ConversationSceneView } from "@/features/worlds/conversation-scene-view";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getConversationPlaybackData } from "@/lib/worlds/server";

type ConversationScenePageProps = {
  params: Promise<{
    worldId: string;
    conversationId: string;
  }>;
};

export default async function ConversationScenePage({ params }: ConversationScenePageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId, conversationId } = await params;
  const data = await getConversationPlaybackData(worldId, conversationId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Scene view"
      intro="Read the conversation as a focused scene with reader-safe media and dialogue."
      worldId={worldId}
    >
      <ConversationSceneView worldId={worldId} conversationId={conversationId} data={data} />
    </WorkspaceShell>
  );
}
