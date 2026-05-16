import { redirect } from "next/navigation";

import { WorldlineBrowser } from "@/features/worlds/worldline-browser";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getWorldlineBrowserData } from "@/lib/worlds/server";

type WorldlineBrowserPageProps = {
  params: Promise<{
    worldId: string;
  }>;
  searchParams: Promise<{
    base?: string;
    compare?: string;
  }>;
};

export default async function WorldlineBrowserPage({
  params,
  searchParams,
}: WorldlineBrowserPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const { base, compare } = await searchParams;
  const data = await getWorldlineBrowserData(worldId, base, compare);

  return (
    <WorkspaceShell
      subject={subject}
      title="Worldlines"
      intro="Browse branches and compare safe worldline summaries without mutating world state."
      worldId={worldId}
    >
      <WorldlineBrowser data={data} />
    </WorkspaceShell>
  );
}
