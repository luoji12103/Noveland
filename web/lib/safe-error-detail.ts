const SENSITIVE_MARKERS = [
  "accesstoken",
  "apikey",
  "authorization",
  "base64",
  "bearertoken",
  "bytes",
  "clientsecret",
  "filesystempath",
  "filepath",
  "localmodelpath",
  "objectpath",
  "objectstoragepath",
  "promptsnapshot",
  "promptsnapshotid",
  "rawbytes",
  "rawoutput",
  "rawprompt",
  "refreshtoken",
  "secretkey",
  "storagepath",
  "storageuri",
  "storageurl",
];

const SENSITIVE_VALUE_PATTERNS = [
  /(?:media|file|s3|gs):\/\//i,
  /(^|[\s"=:(])\/(?:root|home|srv|app|workspace|mnt|var|tmp|models)(?:\/|\b)/i,
  /[A-Za-z]:\\/,
  /sk-[A-Za-z0-9_-]+/i,
  /Bearer\s+\S+/i,
  /\b[A-Za-z0-9+/]{24,}={0,2}\b/,
];

export function normalizeBackendErrorDetail(message: string, fallback: string): string {
  const trimmed = message.trim();
  if (trimmed === "") {
    return fallback;
  }
  return looksSensitiveBackendErrorDetail(trimmed) ? fallback : trimmed;
}

export function looksSensitiveBackendErrorDetail(message: string): boolean {
  const normalized = normalizeMarker(message);
  if (SENSITIVE_MARKERS.some((marker) => normalized.includes(marker))) {
    return true;
  }
  return SENSITIVE_VALUE_PATTERNS.some((pattern) => pattern.test(message));
}

function normalizeMarker(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}
