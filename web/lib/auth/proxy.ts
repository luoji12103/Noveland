import type { NextRequest } from "next/server";

import { CSRF_HEADER_NAME } from "@/lib/auth/types";
import { getAuthApiBaseUrl } from "@/lib/auth/server-config";

type CookieHeaders = Headers & {
  getSetCookie?: () => string[];
};

export async function proxyAuthRequest(
  request: NextRequest,
  authPath: string,
  method: "GET" | "POST",
): Promise<Response> {
  const requestHeaders = buildForwardHeaders(request);
  const requestBody = method === "GET" ? undefined : await request.text();
  const backendResponse = await fetch(`${getAuthApiBaseUrl()}${authPath}`, {
    method,
    headers: requestHeaders,
    body: requestBody || undefined,
    cache: "no-store",
  });

  return buildProxyResponse(backendResponse);
}

export async function buildProxyResponse(backendResponse: Response): Promise<Response> {
  const responseHeaders = new Headers();
  const contentType = backendResponse.headers.get("content-type");
  if (contentType !== null) {
    responseHeaders.set("content-type", contentType);
  }
  responseHeaders.set("cache-control", "no-store");
  for (const cookieHeader of extractSetCookieHeaders(backendResponse.headers)) {
    responseHeaders.append("set-cookie", cookieHeader);
  }

  const responseBody =
    backendResponse.status === 204 ? null : await backendResponse.arrayBuffer();
  return new Response(responseBody, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export function buildStreamingProxyResponse(backendResponse: Response): Response {
  const responseHeaders = new Headers();
  const contentType = backendResponse.headers.get("content-type");
  if (contentType !== null) {
    responseHeaders.set("content-type", contentType);
  } else {
    responseHeaders.set("content-type", "text/event-stream");
  }
  responseHeaders.set("cache-control", "no-store");
  responseHeaders.set("connection", "keep-alive");

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export function extractSetCookieHeaders(headers: Headers): string[] {
  const headersWithCookies = headers as CookieHeaders;
  const setCookieHeaders = headersWithCookies.getSetCookie?.();
  if (setCookieHeaders !== undefined && setCookieHeaders.length > 0) {
    return setCookieHeaders;
  }

  const singleHeader = headers.get("set-cookie");
  return singleHeader === null ? [] : [singleHeader];
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
