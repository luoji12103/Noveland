import { redirect } from "next/navigation";

import { SpeechAdmin } from "@/features/admin/speech-admin";
import { WorkspaceShell } from "@/features/workspace/workspace-shell";
import { getCurrentSubject } from "@/lib/auth/server";
import { getSpeechAdminData } from "@/lib/worlds/server";

type WorldSpeechPageProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export default async function WorldSpeechPage({ params }: WorldSpeechPageProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }

  const { worldId } = await params;
  const data = await getSpeechAdminData(worldId, subject.roles.includes("platform_admin"));

  return (
    <WorkspaceShell
      subject={subject}
      title="Speech"
      intro="Manage voice profiles, agent bindings, style mappings, transcripts, and explicit TTS/STT tests."
      worldId={worldId}
    >
      <SpeechAdmin worldId={worldId} data={data} />
    </WorkspaceShell>
  );
}
