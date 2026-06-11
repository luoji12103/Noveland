import type { NextRequest } from "next/server";

import { buildProxyResponse } from "@/lib/auth/proxy";
import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import { CSRF_HEADER_NAME } from "@/lib/auth/types";

export type PrivateBetaProxyMethod = "GET" | "POST";

export async function proxyPrivateBetaRequest(
  request: NextRequest,
  privateBetaPath: string[],
  method: PrivateBetaProxyMethod,
): Promise<Response> {
  const path = `/private-beta/${privateBetaPath.join("/")}`;
  const requestBody = await proxyRequestBody(request, method);
  const backendResponse = await fetch(`${getAuthApiBaseUrl()}${path}${request.nextUrl.search}`, {
    method,
    headers: buildForwardHeaders(request),
    body: requestBody,
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

async function proxyRequestBody(request: NextRequest, method: PrivateBetaProxyMethod): Promise<ArrayBuffer | undefined> {
  if (method === "GET") {
    return undefined;
  }
  const body = await request.arrayBuffer();
  return body.byteLength === 0 ? undefined : body;
}

function copyHeader(request: NextRequest, headers: Headers, name: string): void {
  const value = request.headers.get(name);
  if (value !== null) {
    headers.set(name, value);
  }
}
