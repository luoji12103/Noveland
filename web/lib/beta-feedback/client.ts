import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";
import type {
  BetaFeedbackIssueType,
  BetaFeedbackReport,
  BetaFeedbackReportCreateInput,
  BetaFeedbackReportStatus,
  BetaFeedbackReportTriageInput,
} from "@/lib/beta-feedback/types";
import { WorldClientError } from "@/lib/worlds/client";

export function listBetaFeedbackReports(
  worldId: string,
  filters: {
    worldline_id?: string | null;
    status?: BetaFeedbackReportStatus | null;
    issue_type?: BetaFeedbackIssueType | null;
  } = {},
): Promise<BetaFeedbackReport[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  appendOptional(search, "issue_type", filters.issue_type);
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  const worldSegment = encodeURIComponent(worldId);
  return betaFeedbackRequest<BetaFeedbackReport[]>(
    `/api/worlds/${worldSegment}/beta-feedback/reports${suffix}`,
    { method: "GET" },
  );
}

export function createBetaFeedbackReport(
  worldId: string,
  input: BetaFeedbackReportCreateInput,
): Promise<BetaFeedbackReport> {
  const worldSegment = encodeURIComponent(worldId);
  return betaFeedbackRequest<BetaFeedbackReport>(`/api/worlds/${worldSegment}/beta-feedback/reports`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function triageBetaFeedbackReport(
  worldId: string,
  reportId: string,
  input: BetaFeedbackReportTriageInput,
): Promise<BetaFeedbackReport> {
  const worldSegment = encodeURIComponent(worldId);
  const reportSegment = encodeURIComponent(reportId);
  return betaFeedbackRequest<BetaFeedbackReport>(
    `/api/worlds/${worldSegment}/beta-feedback/reports/${reportSegment}/triage`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

type RequestOptions = {
  method: "GET" | "POST" | "PATCH";
  body?: unknown;
  csrf?: boolean;
};

async function betaFeedbackRequest<T>(path: string, options: RequestOptions): Promise<T> {
  const headers = new Headers();
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.csrf === true) {
    headers.set(CSRF_HEADER_NAME, await csrfToken());
  }
  const response = await fetch(path, {
    method: options.method,
    headers,
    credentials: "include",
    cache: "no-store",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.ok) {
    return (await response.json()) as T;
  }
  const detail = await errorDetail(response);
  throw new WorldClientError(detail ?? "Beta feedback request failed.", response.status);
}

async function csrfToken(): Promise<string> {
  const existingToken = readCookie(CSRF_COOKIE_NAME);
  if (existingToken !== null) {
    return existingToken;
  }
  const response = await requestCsrf();
  return response.csrf_token;
}

async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

function appendOptional(search: URLSearchParams, key: string, value: string | null | undefined) {
  if (value !== undefined && value !== null && value !== "") {
    search.set(key, value);
  }
}
