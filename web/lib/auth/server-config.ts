const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_API_WS_BASE_URL = "ws://127.0.0.1:8000";

export function getAuthApiBaseUrl(): string {
  const configuredUrl = process.env.NOVELAND_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  return configuredUrl.replace(/\/+$/, "");
}

export function getAuthApiWebSocketBaseUrl(): string {
  const configuredUrl =
    process.env.NEXT_PUBLIC_NOVELAND_API_WS_BASE_URL
    ?? process.env.NOVELAND_API_WS_BASE_URL
    ?? DEFAULT_API_WS_BASE_URL;
  return configuredUrl.replace(/\/+$/, "");
}
