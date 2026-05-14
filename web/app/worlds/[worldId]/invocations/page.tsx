import { redirect } from "next/navigation";

import { InvocationLedgerAdmin } from "@/features/admin/invocation-ledger-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getInvocationLedgerAdminData } from "@/lib/worlds/server";

type WorldInvocationsPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldInvocationsPage({ params }: WorldInvocationsPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getInvocationLedgerAdminData(
    worldId,
    subject.roles.includes("platform_admin"),
  );

  return (
    <WorkspaceShell
      subject={subject}
      title="Invocations"
      intro="Inspect ledger records, prompt snapshot evidence, tags, redaction, visibility, and retention state."
      worldId={worldId}
    >
      <InvocationLedgerAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
