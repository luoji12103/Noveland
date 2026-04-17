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
    `/provider-profiles/${encodeURIComponent((await context.params).profileId)}/test-call`,
    "POST",
  );
}
