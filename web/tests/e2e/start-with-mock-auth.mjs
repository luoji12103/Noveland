import { spawn } from "node:child_process";
import { createServer } from "node:http";

const mockPort = 3207;
const nextPort = 3107;
const validSession = "valid-session";
const validCsrf = "valid-csrf";

const mockServer = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  if (request.method === "GET" && url.pathname === "/auth/csrf") {
    sendJson(response, 200, { csrf_token: validCsrf }, [csrfCookie()]);
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await readJson(request);
    if (body.email === "admin@example.test" && body.password === "correct-password") {
      sendJson(response, 200, subject(), [sessionCookie(), csrfCookie()]);
      return;
    }
    sendJson(response, 401, { detail: "Invalid email or password" });
    return;
  }

  if (request.method === "GET" && url.pathname === "/auth/me") {
    if (hasCookie(request, "noveland_session", validSession)) {
      sendJson(response, 200, subject());
      return;
    }
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/logout") {
    if (!hasCookie(request, "noveland_session", validSession)) {
      sendJson(response, 401, { detail: "Invalid or missing session" });
      return;
    }
    if (request.headers["x-csrf-token"] !== validCsrf) {
      sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
      return;
    }
    response.writeHead(204, {
      "set-cookie": [
        "noveland_session=; Max-Age=0; Path=/; SameSite=Lax; HttpOnly",
        "noveland_csrf=; Max-Age=0; Path=/; SameSite=Lax",
      ],
    });
    response.end();
    return;
  }

  sendJson(response, 404, { detail: "not found" });
});

mockServer.listen(mockPort, "127.0.0.1", () => {
  const nextProcess = spawn(
    "npm",
    ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", String(nextPort)],
    {
      stdio: "inherit",
      env: {
        ...process.env,
        NOVELAND_API_BASE_URL: `http://127.0.0.1:${mockPort}`,
      },
    },
  );

  const shutdown = () => {
    nextProcess.kill("SIGTERM");
    mockServer.close(() => process.exit(0));
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
  nextProcess.on("exit", (code) => {
    mockServer.close(() => process.exit(code ?? 0));
  });
});

function subject() {
  return {
    user_id: "00000000-0000-4000-8000-000000000001",
    email: "admin@example.test",
    display_name: "Admin",
    roles: ["platform_admin"],
  };
}

function sessionCookie() {
  return `noveland_session=${validSession}; Path=/; SameSite=Lax; HttpOnly`;
}

function csrfCookie() {
  return `noveland_csrf=${validCsrf}; Path=/; SameSite=Lax`;
}

function sendJson(response, status, body, setCookie = []) {
  response.writeHead(status, {
    "content-type": "application/json",
    ...(setCookie.length > 0 ? { "set-cookie": setCookie } : {}),
  });
  response.end(JSON.stringify(body));
}

function hasCookie(request, name, expectedValue) {
  return (request.headers.cookie ?? "")
    .split(";")
    .map((cookie) => cookie.trim())
    .some((cookie) => cookie === `${name}=${expectedValue}`);
}

function readJson(request) {
  return new Promise((resolve) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const rawBody = Buffer.concat(chunks).toString("utf8");
      resolve(rawBody === "" ? {} : JSON.parse(rawBody));
    });
  });
}
