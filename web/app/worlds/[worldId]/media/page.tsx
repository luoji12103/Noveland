import { redirect } from "next/navigation";

import { MediaAdmin } from "@/features/admin/media-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getMediaAdminData } from "@/lib/worlds/server";

type WorldMediaPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldMediaPage({ params }: WorldMediaPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getMediaAdminData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title="Media"
      intro="Inspect media assets, objects, jobs, references, uploads, and safe download actions."
      worldId={worldId}
    >
      <MediaAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
