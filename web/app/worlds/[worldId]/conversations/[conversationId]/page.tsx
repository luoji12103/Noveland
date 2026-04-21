import { redirect } from "next/navigation";

import { ConversationDetail } from "@/features/conversations/conversation-detail";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getConversationDetailData } from "@/lib/worlds/server";

type ConversationPageProps = {
  params: Promise<{
    worldId: string;
    conversationId: string;
  }>;
};

export default async function ConversationPage({ params }: ConversationPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId, conversationId } = await params;
  const data = await getConversationDetailData(worldId, conversationId);

  return (
    <WorkspaceShell
      subject={subject}
      title={data.conversation?.title ?? "Conversation"}
      intro="Manage participants, seed the transcript, advance manual chains, or control automated dialogue."
      worldId={worldId}
    >
      <ConversationDetail worldId={worldId} conversationId={conversationId} data={data} />
    </WorkspaceShell>
  );
}
