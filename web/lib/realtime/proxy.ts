import type { NextRequest } from "next/server";

import { buildProxyResponse, buildStreamingProxyResponse } from "@/lib/auth/proxy";
import { getAuthApiBaseUrl } from "@/lib/auth/server-config";

export async function proxyEventStream(
  request: NextRequest,
  backendPath: string,
): Promise<Response> {
  const backendResponse = await fetch(`${getAuthApiBaseUrl()}${backendPath}${request.nextUrl.search}`, {
    method: "GET",
    headers: buildForwardHeaders(request),
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    return buildProxyResponse(backendResponse);
  }
  return buildStreamingProxyResponse(backendResponse);
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  copyHeader(request, headers, "cookie");
  copyHeader(request, headers, "accept");
  copyHeader(request, headers, "cache-control");
  copyHeader(request, headers, "user-agent");
  copyHeader(request, headers, "last-event-id");
  return headers;
}

function copyHeader(request: NextRequest, headers: Headers, name: string): void {
  const value = request.headers.get(name);
  if (value !== null) {
    headers.set(name, value);
  }
}
