import type { NextRequest } from "next/server";

import { proxyRuntimeRequest } from "@/lib/runtime/proxy";

type RouteContext = {
  params: Promise<{
    profileId: string;
  }>;
};

export async function PATCH(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRuntimeRequest(
    request,
    `/provider-profiles/${encodeURIComponent((await context.params).profileId)}`,
    "PATCH",
  );
}

export async function DELETE(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRuntimeRequest(
    request,
    `/provider-profiles/${encodeURIComponent((await context.params).profileId)}`,
    "DELETE",
  );
}
