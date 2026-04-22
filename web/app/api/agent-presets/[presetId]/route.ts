import type { NextRequest } from "next/server";

import { proxyApiRequest } from "@/lib/api-proxy";

type RouteContext = {
  params: Promise<{
    presetId: string;
  }>;
};

export async function PATCH(request: NextRequest, context: RouteContext): Promise<Response> {
  const { presetId } = await context.params;
  return proxyApiRequest(request, `/agent-presets/${encodeURIComponent(presetId)}`, "PATCH");
}

export async function DELETE(request: NextRequest, context: RouteContext): Promise<Response> {
  const { presetId } = await context.params;
  return proxyApiRequest(request, `/agent-presets/${encodeURIComponent(presetId)}`, "DELETE");
}
