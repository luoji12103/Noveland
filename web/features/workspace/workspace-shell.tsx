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
        {worldId !== null ? (
          <>
            <Link href={`/worlds/${worldId}`}>Overview</Link>
            <Link href={`/worlds/${worldId}/agents`}>Agents</Link>
            <Link href={`/worlds/${worldId}/conversations`}>Conversations</Link>
            <Link href={`/worlds/${worldId}/providers`}>Providers</Link>
            <Link href={`/worlds/${worldId}/media`}>Media</Link>
            <Link href={`/worlds/${worldId}/visual`}>Visual</Link>
            <Link href={`/worlds/${worldId}/speech`}>Speech</Link>
            <Link href={`/worlds/${worldId}/invocations`}>Invocations</Link>
            <Link href={`/worlds/${worldId}/narrative`}>Narrative</Link>
            <Link href={`/worlds/${worldId}/reader`}>Reader</Link>
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
