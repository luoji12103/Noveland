import { redirect } from "next/navigation";

import { BetaFeedbackPanel } from "@/features/private-beta/beta-feedback-panel";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getBetaFeedbackData } from "@/lib/beta-feedback/server";

type FeedbackPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function FeedbackPage({ params }: FeedbackPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getBetaFeedbackData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title="Beta feedback"
      intro="Submit private beta issues and triage contextual reports without exposing provider or media internals."
      worldId={worldId}
    >
      <BetaFeedbackPanel data={data} worldId={worldId} />
    </WorkspaceShell>
  );
}
