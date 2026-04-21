import { redirect } from "next/navigation";

import { WorldsIndex } from "@/features/worlds/worlds-index";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getWorldsIndexData } from "@/lib/worlds/server";

export default async function WorldsPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const worlds = await getWorldsIndexData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Worlds"
      intro="Create and open worlds before configuring scenes, agents, conversations, and runtime data."
    >
      <WorldsIndex worlds={worlds} canCreateWorld={subject.roles.includes("platform_admin")} />
    </WorkspaceShell>
  );
}
