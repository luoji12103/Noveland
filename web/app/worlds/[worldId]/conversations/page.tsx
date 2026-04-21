import { redirect } from "next/navigation";

import { ConversationList } from "@/features/conversations/conversation-list";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getConversationListData } from "@/lib/worlds/server";

type ConversationsPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function ConversationsPage({ params }: ConversationsPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getConversationListData(worldId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Conversations"
      intro="Create scene-scoped or world-scoped sessions for manual chains and automated multi-agent dialogue."
      worldId={worldId}
    >
      <ConversationList worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
