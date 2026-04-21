import { redirect } from "next/navigation";

import { LoginForm } from "@/features/auth/login-form";
import { getCurrentSubject } from "@/lib/auth/server";

export default async function LoginPage() {
  const subject = await getCurrentSubject();
  if (subject !== null) {
    redirect("/worlds");
  }

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <p className="eyebrow">Noveland control surface</p>
        <h1 className="login-title" id="login-title">
          Sign in to Noveland
        </h1>
        <p className="login-copy">
          Use the local platform admin account seeded from the backend command line.
        </p>
        <LoginForm />
      </section>
    </main>
  );
}
