import { redirect } from "next/navigation";

import { AgentBuilder } from "@/features/agents/agent-builder";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getAgentDetailData } from "@/lib/worlds/server";

type AgentPageProps = {
  params: Promise<{
    worldId: string;
    agentId: string;
  }>;
};

export default async function AgentPage({ params }: AgentPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId, agentId } = await params;
  const data = await getAgentDetailData(
    worldId,
    agentId,
    subject.roles.includes("platform_admin"),
  );

  return (
    <WorkspaceShell
      subject={subject}
      title={data.selectedAgent?.display_name ?? "Agent builder"}
      intro="Edit agent profile, persona, observations, calendar, memory, and manual runtime runs in one focused builder."
      worldId={worldId}
    >
      <AgentBuilder worldId={worldId} agentId={agentId} data={data} />
    </WorkspaceShell>
  );
}
