import type { NextRequest } from "next/server";

import { proxyRuntimeRequest } from "@/lib/runtime/proxy";

type RouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRuntimeRequest(
    request,
    `/memory-backend-profiles/${encodeURIComponent((await context.params).profileId)}/eval-smoke`,
    "POST",
  );
}
