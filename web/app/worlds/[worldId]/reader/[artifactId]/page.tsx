import { redirect } from "next/navigation";

import { NarrativeReaderDetail } from "@/features/worlds/narrative-reader";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getNarrativeReaderDetailData } from "@/lib/worlds/server";

type NarrativeReaderDetailPageProps = {
  params: Promise<{
    worldId: string;
    artifactId: string;
  }>;
};

export default async function NarrativeReaderDetailPage({
  params,
}: NarrativeReaderDetailPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId, artifactId } = await params;
  const data = await getNarrativeReaderDetailData(worldId, artifactId);

  return (
    <WorkspaceShell
      subject={subject}
      title="Reader detail"
      intro="Review a single narrative artifact with its source metadata and conversation linkage."
      worldId={worldId}
    >
      <NarrativeReaderDetail worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
