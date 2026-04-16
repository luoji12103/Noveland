import Image from "next/image";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/features/auth/logout-button";
import { StatusCards } from "@/features/dashboard/status-cards";
import { WorldManagementDashboard } from "@/features/dashboard/world-management-dashboard";
import { getCurrentSubject } from "@/lib/auth/server";
import { systemStatuses } from "@/lib/status";
import { getWorldDashboardData } from "@/lib/worlds/server";

type HomeProps = {
  searchParams?: Promise<{
    world?: string;
  }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const subject = await getCurrentSubject();
  if (subject === null) {
    redirect("/login");
  }
  const resolvedSearchParams = await searchParams;
  const dashboardData = await getWorldDashboardData(resolvedSearchParams?.world ?? null);

  return (
    <main className="page-shell">
      <section className="top-band">
        <div className="top-band-inner">
          <div>
            <p className="eyebrow">Noveland control surface</p>
            <h1 className="title">World management console</h1>
            <p className="intro">
              Manage worlds, scenes, agents, and memberships from the local control surface.
            </p>
          </div>
          <Image
            className="world-image"
            src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80"
            width={1200}
            height={800}
            priority
            alt="Mountain lake at sunrise"
          />
        </div>
      </section>

      <section className="session-strip" aria-label="Current session">
        <div>
          <p className="session-label">Signed in</p>
          <p className="session-user">
            {subject.display_name} - {subject.email}
          </p>
          <p className="session-roles">{subject.roles.join(", ")}</p>
        </div>
        <LogoutButton />
      </section>

      <WorldManagementDashboard subject={subject} initialData={dashboardData} />

      <section className="status-section">
        <h2 className="section-title">System status</h2>
        <StatusCards statuses={systemStatuses} />
      </section>
    </main>
  );
}
