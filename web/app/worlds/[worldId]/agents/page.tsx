import { redirect } from "next/navigation";

import { AgentList } from "@/features/agents/agent-list";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getAgentWorkspaceData } from "@/lib/worlds/server";

type AgentsPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function AgentsPage({ params }: AgentsPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getAgentWorkspaceData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title="Agents"
      intro="Build role and narrative agents with structured identity, scene, provider, persona, memory, and run controls."
      worldId={worldId}
    >
      <AgentList worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
