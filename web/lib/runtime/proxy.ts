import type { NextRequest } from "next/server";

import { buildProxyResponse } from "@/lib/auth/proxy";
import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import { CSRF_HEADER_NAME } from "@/lib/auth/types";

type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export async function proxyRuntimeRequest(
  request: NextRequest,
  path: string,
  method: ProxyMethod,
): Promise<Response> {
  const requestBody = method === "GET" ? undefined : await request.text();
  const backendResponse = await fetch(`${getAuthApiBaseUrl()}${path}${request.nextUrl.search}`, {
    method,
    headers: buildForwardHeaders(request),
    body: requestBody || undefined,
    cache: "no-store",
  });
  return buildProxyResponse(backendResponse);
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  copyHeader(request, headers, "cookie");
  copyHeader(request, headers, "content-type");
  copyHeader(request, headers, "user-agent");
  copyHeader(request, headers, CSRF_HEADER_NAME);
  return headers;
}

function copyHeader(request: NextRequest, headers: Headers, name: string): void {
  const value = request.headers.get(name);
  if (value !== null) {
    headers.set(name, value);
  }
}
