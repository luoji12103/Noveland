import { redirect } from "next/navigation";

import { ProviderIntegrationAdmin } from "@/features/admin/provider-integration-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getProviderIntegrationAdminData } from "@/lib/worlds/server";

type WorldProvidersPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldProvidersPage({ params }: WorldProvidersPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getProviderIntegrationAdminData(
    worldId,
    subject.roles.includes("platform_admin"),
  );

  return (
    <WorkspaceShell
      subject={subject}
      title="Providers"
      intro="Manage world provider integrations, capability evidence, health checks, and safe smoke tests."
      worldId={worldId}
    >
      <ProviderIntegrationAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
