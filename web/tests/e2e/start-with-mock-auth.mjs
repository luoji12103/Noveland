import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const mockPort = 3207;
const nextPort = 3107;
const validCsrf = "valid-csrf";
const adminSession = "admin-session";
const memberSession = "member-session";
const adminUserId = "00000000-0000-4000-8000-000000000001";
const memberUserId = "00000000-0000-4000-8000-000000000002";
const candidateUserId = "00000000-0000-4000-8000-000000000003";
const worldOneId = "10000000-0000-4000-8000-000000000001";
const sceneHomeId = "20000000-0000-4000-8000-000000000001";
const agentGuideId = "30000000-0000-4000-8000-000000000001";
const membershipOwnerId = "40000000-0000-4000-8000-000000000001";
const membershipMemberId = "40000000-0000-4000-8000-000000000002";

const users = [
  user(adminUserId, "admin@example.test", "Admin"),
  user(memberUserId, "member@example.test", "Member"),
  user(candidateUserId, "candidate@example.test", "Candidate"),
];
const sessionSubjects = new Map([
  [adminSession, subject(adminUserId, "admin@example.test", "Admin", ["platform_admin"])],
  [memberSession, subject(memberUserId, "member@example.test", "Member", [])],
]);
const worlds = [
  {
    id: worldOneId,
    owner_user_id: adminUserId,
    slug: "first-world",
    name: "First World",
    description: "A managed world",
    rules_config: {},
    is_active: true,
  },
];
const scenes = [
  {
    id: sceneHomeId,
    world_id: worldOneId,
    scene_key: "home",
    name: "Home",
    description: null,
    is_active: true,
  },
];
const agents = [
  {
    id: agentGuideId,
    world_id: worldOneId,
    home_scene_id: sceneHomeId,
    agent_key: "guide",
    display_name: "Guide",
    kind: "role_agent",
    config: {},
    is_enabled: true,
  },
];
const memberships = [
  membership(membershipOwnerId, worldOneId, adminUserId, "world_admin"),
  membership(membershipMemberId, worldOneId, memberUserId, "human_user"),
];

const mockServer = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  if (request.method === "GET" && url.pathname === "/auth/csrf") {
    sendJson(response, 200, { csrf_token: validCsrf }, [csrfCookie()]);
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/login") {
    const body = await readJson(request);
    if (body.email === "admin@example.test" && body.password === "correct-password") {
      sendJson(response, 200, sessionSubjects.get(adminSession), [
        sessionCookie(adminSession),
        csrfCookie(),
      ]);
      return;
    }
    if (body.email === "member@example.test" && body.password === "correct-password") {
      sendJson(response, 200, sessionSubjects.get(memberSession), [
        sessionCookie(memberSession),
        csrfCookie(),
      ]);
      return;
    }
    sendJson(response, 401, { detail: "Invalid email or password" });
    return;
  }

  if (request.method === "GET" && url.pathname === "/auth/me") {
    const currentSubject = subjectForRequest(request);
    if (currentSubject !== null) {
      sendJson(response, 200, currentSubject);
      return;
    }
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }

  if (request.method === "POST" && url.pathname === "/auth/logout") {
    if (subjectForRequest(request) === null) {
      sendJson(response, 401, { detail: "Invalid or missing session" });
      return;
    }
    if (!hasValidCsrf(request)) {
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

  if (url.pathname === "/worlds") {
    await handleWorldCollection(request, response);
    return;
  }

  if (url.pathname.startsWith("/worlds/")) {
    await handleWorldResource(request, response, url);
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

async function handleWorldCollection(request, response) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  if (request.method === "GET") {
    const visibleWorlds = isPlatformAdmin(currentSubject)
      ? worlds
      : worlds.filter((world) => membershipFor(world.id, currentSubject.user_id) !== undefined);
    sendJson(response, 200, visibleWorlds);
    return;
  }
  if (request.method === "POST") {
    if (!isPlatformAdmin(currentSubject)) {
      sendJson(response, 403, { detail: "Forbidden" });
      return;
    }
    if (!hasValidCsrf(request)) {
      sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
      return;
    }
    const body = await readJson(request);
    if (worlds.some((world) => world.slug === body.slug)) {
      sendJson(response, 409, { detail: "World slug already exists" });
      return;
    }
    const world = {
      id: randomUUID(),
      owner_user_id: currentSubject.user_id,
      slug: body.slug,
      name: body.name,
      description: body.description ?? null,
      rules_config: body.rules_config ?? {},
      is_active: true,
    };
    worlds.push(world);
    memberships.push(membership(randomUUID(), world.id, currentSubject.user_id, "world_admin"));
    sendJson(response, 201, world);
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleWorldResource(request, response, url) {
  const currentSubject = subjectForRequest(request);
  if (currentSubject === null) {
    sendJson(response, 401, { detail: "Invalid or missing session" });
    return;
  }
  const segments = url.pathname.split("/").filter(Boolean);
  const worldId = segments[1];
  const world = worlds.find((item) => item.id === worldId);
  if (world === undefined || !canReadWorld(currentSubject, worldId)) {
    sendJson(response, 404, { detail: "World not found" });
    return;
  }

  if (segments.length === 2) {
    await handleWorldItem(request, response, currentSubject, world);
    return;
  }

  const resource = segments[2];
  if (resource === "scenes") {
    await handleScenes(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "agents") {
    await handleAgents(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "memberships") {
    await handleMemberships(request, response, currentSubject, worldId, segments[3]);
    return;
  }
  if (resource === "member-candidates") {
    handleMemberCandidates(request, response, currentSubject, worldId, url);
    return;
  }
  sendJson(response, 404, { detail: "not found" });
}

async function handleWorldItem(request, response, currentSubject, world) {
  if (request.method === "GET") {
    sendJson(response, 200, world);
    return;
  }
  if (!canManageWorld(currentSubject, world.id)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(world, await readJson(request));
    sendJson(response, 200, world);
    return;
  }
  if (request.method === "DELETE") {
    world.is_active = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleScenes(request, response, currentSubject, worldId, sceneId) {
  if (request.method === "GET" && sceneId === undefined) {
    sendJson(response, 200, scenes.filter((scene) => scene.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && sceneId === undefined) {
    const body = await readJson(request);
    if (scenes.some((scene) => scene.world_id === worldId && scene.scene_key === body.scene_key)) {
      sendJson(response, 409, { detail: "Scene key already exists" });
      return;
    }
    const scene = {
      id: randomUUID(),
      world_id: worldId,
      scene_key: body.scene_key,
      name: body.name,
      description: body.description ?? null,
      is_active: true,
    };
    scenes.push(scene);
    sendJson(response, 201, scene);
    return;
  }
  const scene = scenes.find((item) => item.id === sceneId && item.world_id === worldId);
  if (scene === undefined) {
    sendJson(response, 404, { detail: "Scene not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(scene, await readJson(request));
    sendJson(response, 200, scene);
    return;
  }
  if (request.method === "DELETE") {
    scene.is_active = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleAgents(request, response, currentSubject, worldId, agentId) {
  if (request.method === "GET" && agentId === undefined) {
    sendJson(response, 200, agents.filter((agent) => agent.world_id === worldId));
    return;
  }
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "POST" && agentId === undefined) {
    const body = await readJson(request);
    if (agents.some((agent) => agent.world_id === worldId && agent.agent_key === body.agent_key)) {
      sendJson(response, 409, { detail: "Agent key already exists" });
      return;
    }
    const agent = {
      id: randomUUID(),
      world_id: worldId,
      home_scene_id: body.home_scene_id ?? null,
      agent_key: body.agent_key,
      display_name: body.display_name,
      kind: body.kind,
      config: body.config ?? {},
      is_enabled: true,
    };
    agents.push(agent);
    sendJson(response, 201, agent);
    return;
  }
  const agent = agents.find((item) => item.id === agentId && item.world_id === worldId);
  if (agent === undefined) {
    sendJson(response, 404, { detail: "Agent not found" });
    return;
  }
  if (request.method === "PATCH") {
    Object.assign(agent, await readJson(request));
    sendJson(response, 200, agent);
    return;
  }
  if (request.method === "DELETE") {
    agent.is_enabled = false;
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

async function handleMemberships(request, response, currentSubject, worldId, userId) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  if (request.method === "GET" && userId === undefined) {
    sendJson(response, 200, memberships.filter((item) => item.world_id === worldId).map(expandMembership));
    return;
  }
  if (!hasValidCsrf(request)) {
    sendJson(response, 403, { detail: "CSRF token is missing or invalid" });
    return;
  }
  if (request.method === "PUT" && userId !== undefined) {
    const body = await readJson(request);
    let currentMembership = membershipFor(worldId, userId);
    if (currentMembership === undefined) {
      currentMembership = membership(randomUUID(), worldId, userId, body.role);
      memberships.push(currentMembership);
    } else {
      currentMembership.role = body.role;
    }
    sendJson(response, 200, expandMembership(currentMembership));
    return;
  }
  if (request.method === "DELETE" && userId !== undefined) {
    const currentMembership = membershipFor(worldId, userId);
    if (currentMembership === undefined) {
      sendJson(response, 404, { detail: "Membership not found" });
      return;
    }
    const adminCount = memberships.filter(
      (item) => item.world_id === worldId && item.role === "world_admin",
    ).length;
    if (currentMembership.role === "world_admin" && adminCount <= 1) {
      sendJson(response, 409, { detail: "Cannot remove the final world admin" });
      return;
    }
    memberships.splice(memberships.indexOf(currentMembership), 1);
    response.writeHead(204);
    response.end();
    return;
  }
  sendJson(response, 405, { detail: "method not allowed" });
}

function handleMemberCandidates(request, response, currentSubject, worldId, url) {
  if (!canManageWorld(currentSubject, worldId)) {
    sendJson(response, 403, { detail: "Forbidden" });
    return;
  }
  const query = (url.searchParams.get("query") ?? "").toLowerCase();
  const limit = Math.min(Number(url.searchParams.get("limit") ?? "20"), 50);
  const candidates = users
    .filter((item) => item.is_active)
    .filter(
      (item) =>
        query === ""
        || item.email.toLowerCase().includes(query)
        || item.display_name.toLowerCase().includes(query),
    )
    .slice(0, limit)
    .map((item) => ({ ...item, role: membershipFor(worldId, item.id)?.role ?? null }));
  sendJson(response, 200, candidates);
}

function subject(user_id, email, display_name, roles) {
  return { user_id, email, display_name, roles };
}

function user(id, email, display_name) {
  return { id, email, display_name, is_active: true };
}

function membership(id, world_id, user_id, role) {
  return { id, world_id, user_id, role };
}

function expandMembership(currentMembership) {
  return {
    ...currentMembership,
    user: users.find((item) => item.id === currentMembership.user_id),
  };
}

function sessionCookie(token) {
  return `noveland_session=${token}; Path=/; SameSite=Lax; HttpOnly`;
}

function csrfCookie() {
  return `noveland_csrf=${validCsrf}; Path=/; SameSite=Lax`;
}

function subjectForRequest(request) {
  const sessionCookieValue = (request.headers.cookie ?? "")
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith("noveland_session="));
  if (sessionCookieValue === undefined) {
    return null;
  }
  const token = sessionCookieValue.slice("noveland_session=".length);
  return sessionSubjects.get(token) ?? null;
}

function canReadWorld(currentSubject, worldId) {
  return isPlatformAdmin(currentSubject) || membershipFor(worldId, currentSubject.user_id) !== undefined;
}

function canManageWorld(currentSubject, worldId) {
  return (
    isPlatformAdmin(currentSubject)
    || membershipFor(worldId, currentSubject.user_id)?.role === "world_admin"
  );
}

function isPlatformAdmin(currentSubject) {
  return currentSubject.roles.includes("platform_admin");
}

function membershipFor(worldId, userId) {
  return memberships.find((item) => item.world_id === worldId && item.user_id === userId);
}

function hasValidCsrf(request) {
  return hasCookie(request, "noveland_csrf", validCsrf) && request.headers["x-csrf-token"] === validCsrf;
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
