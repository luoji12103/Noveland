import type { NextRequest } from "next/server";

import { proxyRuntimeRequest } from "@/lib/runtime/proxy";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRuntimeRequest(
    request,
    `/memory-write-jobs/${encodeURIComponent((await context.params).jobId)}/retry`,
    "POST",
  );
}
