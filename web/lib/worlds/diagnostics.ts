import { adminRequest } from "@/lib/admin/api-client";

export type MultimodalFindingSeverity = "info" | "warning" | "blocker";
export type MultimodalEvalStatus = "completed" | "warning" | "failed";

export type MultimodalEvidenceRef = {
  kind: string;
  id: string;
};

export type MultimodalDiagnosticFinding = {
  code: string;
  severity: MultimodalFindingSeverity;
  message: string;
  evidence_refs: MultimodalEvidenceRef[];
};

export type MultimodalDiagnosticsResult = {
  world_id: string;
  worldline_id: string;
  status: MultimodalEvalStatus;
  metrics: Record<string, unknown>;
  blockers: MultimodalDiagnosticFinding[];
  warnings: MultimodalDiagnosticFinding[];
  recommendations: string[];
  evidence_refs: MultimodalEvidenceRef[];
  generated_at: string;
};

export type MultimodalEvalRunRequest = {
  worldline_id?: string | null;
  eval_key?: string;
  horizon_days?: number;
  metadata?: Record<string, unknown>;
};

export type MultimodalEvalRun = {
  id: string;
  world_id: string;
  worldline_id: string;
  eval_key: string;
  horizon_days: number;
  status: MultimodalEvalStatus;
  started_at: string;
  finished_at: string;
  metrics: Record<string, unknown>;
  recommendations: Array<Record<string, unknown>>;
  blockers: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MultimodalDiagnosticsFilters = {
  worldline_id?: string | null;
};

export type MultimodalEvalRunFilters = MultimodalDiagnosticsFilters & {
  limit?: number;
};

export function getMultimodalDiagnostics(
  worldId: string,
  filters: MultimodalDiagnosticsFilters = {},
): Promise<MultimodalDiagnosticsResult> {
  return adminRequest<MultimodalDiagnosticsResult>(
    `/api/worlds/${worldId}/diagnostics/multimodal${query(filters)}`,
    { method: "GET" },
  );
}

export function listMultimodalEvalRuns(
  worldId: string,
  filters: MultimodalEvalRunFilters = {},
): Promise<MultimodalEvalRun[]> {
  return adminRequest<MultimodalEvalRun[]>(
    `/api/worlds/${worldId}/multimodal-evals${query(filters)}`,
    { method: "GET" },
  );
}

export function getMultimodalEvalRun(
  worldId: string,
  runId: string,
): Promise<MultimodalEvalRun> {
  return adminRequest<MultimodalEvalRun>(
    `/api/worlds/${worldId}/multimodal-evals/${runId}`,
    { method: "GET" },
  );
}

export function runMultimodalEval(
  worldId: string,
  input: MultimodalEvalRunRequest = {},
): Promise<MultimodalEvalRun> {
  return adminRequest<MultimodalEvalRun>(
    `/api/worlds/${worldId}/multimodal-evals/run`,
    {
      method: "POST",
      body: {
        eval_key: input.eval_key ?? "multimodal-smoke",
        horizon_days: input.horizon_days ?? 7,
        metadata: input.metadata ?? { source: "web_admin" },
        worldline_id: input.worldline_id ?? null,
      },
      csrf: true,
    },
  );
}

function query(filters: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if ((typeof value === "string" || typeof value === "number" || typeof value === "boolean") && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.size === 0 ? "" : `?${search.toString()}`;
}
