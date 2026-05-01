import type { NextRequest } from "next/server";

import { proxyRuntimeRequest } from "@/lib/runtime/proxy";

type RouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  const url = new URL(request.url);
  const search = url.search === "" ? "" : url.search;
  return proxyRuntimeRequest(
    request,
    `/memory-backend-profiles/${encodeURIComponent((await context.params).profileId)}/logs${search}`,
    "GET",
  );
}
