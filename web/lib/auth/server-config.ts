const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function getAuthApiBaseUrl(): string {
  const configuredUrl = process.env.NOVELAND_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  return configuredUrl.replace(/\/+$/, "");
}
