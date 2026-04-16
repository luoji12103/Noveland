"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthClientError, login, requestCsrf } from "@/lib/auth/client";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (email.trim() === "" || password === "") {
      setError("Email and password are required.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await requestCsrf();
      await login({ email, password });
      router.replace("/");
      router.refresh();
    } catch (caughtError) {
      setError(messageForError(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <label className="field-label" htmlFor="email">
        Email
      </label>
      <input
        className="text-input"
        id="email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />

      <label className="field-label" htmlFor="password">
        Password
      </label>
      <input
        className="text-input"
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      {error !== null ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <button className="primary-button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Signing in" : "Sign in"}
      </button>
    </form>
  );
}

function messageForError(error: unknown): string {
  if (error instanceof AuthClientError) {
    if (error.status === 401) {
      return "Invalid email or password.";
    }
    if (error.status === 422) {
      return "Enter a valid email and password.";
    }
  }
  return "Unable to sign in. Check that the API is running.";
}
