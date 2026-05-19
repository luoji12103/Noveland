import { redirect } from "next/navigation";

import { PrivateBetaOnboarding } from "@/features/private-beta/private-beta-onboarding";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getPrivateBetaOnboardingData } from "@/lib/private-beta/server";

export default async function PrivateBetaPage() {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const data = await getPrivateBetaOnboardingData();

  return (
    <WorkspaceShell
      subject={subject}
      title="Private beta access"
      intro="Redeem an invitation and create a player identity before entering an invited world."
    >
      <PrivateBetaOnboarding data={data} />
    </WorkspaceShell>
  );
}
