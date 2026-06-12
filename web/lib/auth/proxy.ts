import type { NextRequest } from "next/server";

import { CSRF_HEADER_NAME } from "@/lib/auth/types";
import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import {
  looksSensitiveBackendErrorDetail,
  normalizeBackendErrorDetail,
} from "@/lib/safe-error-detail";

type CookieHeaders = Headers & {
  getSetCookie?: () => string[];
};

type ProxyResponseBody = { body: BodyInit | null; sanitized: boolean };

type SanitizedProxyErrorValue = { value: unknown; sanitized: boolean };

type ProxyResponseOptions = {
  relaySetCookie?: boolean;
};

const SAFE_PROXY_RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "content-length",
  "x-content-type-options",
];

export async function proxyAuthRequest(
  request: NextRequest,
  authPath: string,
  method: "GET" | "POST",
): Promise<Response> {
  const requestHeaders = buildForwardHeaders(request);
  const requestBody = await proxyRequestBody(request, method);
  const backendResponse = await fetch(`${getAuthApiBaseUrl()}${authPath}`, {
    method,
    headers: requestHeaders,
    body: requestBody,
    cache: "no-store",
  });

  return buildProxyResponse(backendResponse, { relaySetCookie: true });
}

export async function buildProxyResponse(
  backendResponse: Response,
  options: ProxyResponseOptions = {},
): Promise<Response> {
  const responseHeaders = new Headers();
  copySafeProxyResponseHeaders(backendResponse.headers, responseHeaders);
  responseHeaders.set("cache-control", "no-store");
  if (options.relaySetCookie === true) {
    for (const cookieHeader of extractSetCookieHeaders(backendResponse.headers)) {
      responseHeaders.append("set-cookie", cookieHeader);
    }
  }

  const { body: responseBody, sanitized } = await proxyResponseBody(backendResponse);
  if (sanitized) {
    responseHeaders.delete("content-length");
  }
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

function copySafeProxyResponseHeaders(source: Headers, target: Headers): void {
  for (const headerName of SAFE_PROXY_RESPONSE_HEADERS) {
    const value = source.get(headerName);
    if (value !== null) {
      target.set(headerName, value);
    }
  }
}

async function proxyResponseBody(backendResponse: Response): Promise<ProxyResponseBody> {
  if (backendResponse.status === 204) {
    return { body: null, sanitized: false };
  }
  if (shouldSanitizeJsonErrorBody(backendResponse)) {
    const text = await backendResponse.text();
    const sanitizedText = sanitizeProxyErrorJson(text);
    return sanitizedText === null
      ? { body: text, sanitized: false }
      : { body: sanitizedText, sanitized: true };
  }
  return { body: await backendResponse.arrayBuffer(), sanitized: false };
}

function shouldSanitizeJsonErrorBody(response: Response): boolean {
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  return !response.ok && contentType.includes("application/json");
}

function sanitizeProxyErrorJson(text: string): string | null {
  try {
    const result = sanitizeProxyErrorValue(JSON.parse(text) as unknown, "Request failed.");
    return result.sanitized ? JSON.stringify(result.value) : null;
  } catch {
    return null;
  }
}

function sanitizeProxyErrorValue(value: unknown, fallback: string): SanitizedProxyErrorValue {
  if (typeof value === "string") {
    const normalized = normalizeBackendErrorDetail(value, fallback);
    return { value: normalized, sanitized: normalized !== value };
  }
  if (Array.isArray(value)) {
    let sanitized = false;
    const output = value.map((item) => {
      const result = sanitizeProxyErrorValue(item, "[redacted]");
      sanitized ||= result.sanitized;
      return result.value;
    });
    return { value: sanitized ? output : value, sanitized };
  }
  if (value !== null && typeof value === "object") {
    let sanitized = false;
    const output: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value)) {
      if (looksSensitiveBackendErrorDetail(key)) {
        sanitized = true;
        continue;
      }
      const result = sanitizeProxyErrorValue(
        entry,
        key === "detail" || key === "message" ? "Request failed." : "[redacted]",
      );
      sanitized ||= result.sanitized;
      output[key] = result.value;
    }
    return { value: sanitized ? output : value, sanitized };
  }
  return { value, sanitized: false };
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  copyHeader(request, headers, "cookie");
  copyHeader(request, headers, "content-type");
  copyHeader(request, headers, "user-agent");
  copyHeader(request, headers, CSRF_HEADER_NAME);
  return headers;
}

async function proxyRequestBody(request: NextRequest, method: "GET" | "POST"): Promise<ArrayBuffer | undefined> {
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
