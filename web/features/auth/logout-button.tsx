"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { logout } from "@/lib/auth/client";

export function LogoutButton() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleLogout() {
    setError(null);
    setIsSubmitting(true);
    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch {
      setError("Unable to sign out. Refresh and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="logout-control">
      <button className="secondary-button" type="button" onClick={handleLogout} disabled={isSubmitting}>
        {isSubmitting ? "Signing out" : "Log out"}
      </button>
      {error !== null ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
