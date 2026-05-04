import { redirect } from "next/navigation";

import { NarrativeReaderList } from "@/features/worlds/narrative-reader";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getNarrativeReaderListData } from "@/lib/worlds/server";

type NarrativeReaderPageProps = {
  params: Promise<{
    worldId: string;
  }>;
  searchParams: Promise<{
    artifact_kind?: string;
    source_conversation_id?: string;
    q?: string;
    source_kind?: "world" | "agent" | "agent_run" | "conversation";
  }>;
};

export default async function NarrativeReaderPage({
  params,
  searchParams,
}: NarrativeReaderPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const filters = await searchParams;
  const data = await getNarrativeReaderListData(worldId, {
    artifact_kind: filters.artifact_kind ?? null,
    source_conversation_id: filters.source_conversation_id ?? null,
    q: filters.q ?? null,
    source_kind: filters.source_kind ?? null,
    limit: 100,
  });

  return (
    <WorkspaceShell
      subject={subject}
      title="Reader"
      intro="Read world summaries, conversation summaries, and chapter drafts without the management controls."
      worldId={worldId}
    >
      <NarrativeReaderList worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
