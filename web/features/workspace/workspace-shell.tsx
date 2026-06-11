import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/features/auth/logout-button";
import type { AuthSubject } from "@/lib/auth/types";

type WorkspaceShellProps = {
  subject: AuthSubject;
  title: string;
  intro: string;
  worldId?: string | null;
  children: ReactNode;
};

export function WorkspaceShell({
  subject,
  title,
  intro,
  worldId = null,
  children,
}: WorkspaceShellProps) {
  const isPlatformAdmin = subject.roles.includes("platform_admin");
  const worldPath = worldId === null ? null : `/worlds/${encodeURIComponent(worldId)}`;

  return (
    <main className="page-shell">
      <section className="top-band">
        <div className="top-band-inner">
          <div>
            <p className="eyebrow">Noveland workspace</p>
            <h1 className="title">{title}</h1>
            <p className="intro">{intro}</p>
          </div>
          <Image
            className="world-image"
            src="https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1200&q=80"
            width={1200}
            height={800}
            priority
            alt="Night sky over mountains"
          />
        </div>
      </section>

      <section className="session-strip" aria-label="Current session">
        <div>
          <p className="session-label">Signed in</p>
          <p className="session-user">
            {subject.display_name} - {subject.email}
          </p>
          <p className="session-roles">{subject.roles.join(", ") || "world member"}</p>
        </div>
        <LogoutButton />
      </section>

      <nav className="workspace-nav" aria-label="Workspace navigation">
        <Link href="/worlds">Worlds</Link>
        {worldPath !== null ? (
          <>
            <Link href={`${worldPath}`}>Overview</Link>
            <Link href={`${worldPath}/agents`}>Agents</Link>
            <Link href={`${worldPath}/conversations`}>Conversations</Link>
            <Link href={`${worldPath}/providers`}>Providers</Link>
            <Link href={`${worldPath}/media`}>Media</Link>
            <Link href={`${worldPath}/visual`}>Visual</Link>
            <Link href={`${worldPath}/speech`}>Speech</Link>
            <Link href={`${worldPath}/invocations`}>Invocations</Link>
            <Link href={`${worldPath}/diagnostics`}>Diagnostics</Link>
            <Link href={`${worldPath}/narrative`}>Narrative</Link>
            <Link href={`${worldPath}/reader`}>Reader</Link>
            <Link href={`${worldPath}/player`}>Player</Link>
            <Link href={`${worldPath}/feedback`}>Feedback</Link>
            <Link href={`${worldPath}/worldlines`}>Worldlines</Link>
          </>
        ) : null}
        {isPlatformAdmin ? (
          <>
            <Link href="/admin/memory-backends">Memory backends</Link>
            <Link href="/admin/presets">Presets</Link>
            <Link href="/admin/providers">Providers</Link>
            <Link href="/admin/runtime">Runtime</Link>
          </>
        ) : null}
      </nav>

      {children}
    </main>
  );
}
