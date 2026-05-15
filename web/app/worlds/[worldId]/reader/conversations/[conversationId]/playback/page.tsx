import { redirect } from "next/navigation";

import { ConversationPlayback } from "@/features/worlds/conversation-playback";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getConversationPlaybackData } from "@/lib/worlds/server";

type ConversationPlaybackPageProps = {
  params: Promise<{
    worldId: string;
    conversationId: string;
  }>;
};

export default async function ConversationPlaybackPage({ params }: ConversationPlaybackPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId, conversationId } = await params;
  const data = await getConversationPlaybackData(worldId, conversationId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Conversation playback"
      intro="Read the conversation as a turn sequence with reader-safe presentation media."
      worldId={worldId}
    >
      <ConversationPlayback worldId={worldId} conversationId={conversationId} data={data} />
    </WorkspaceShell>
  );
}
