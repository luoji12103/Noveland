import type { NextRequest } from "next/server";

import { proxyApiRequest } from "@/lib/api-proxy";

type RouteContext = {
  params: Promise<{
    presetId: string;
  }>;
};

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  const { presetId } = await context.params;
  return proxyApiRequest(
    request,
    `/agent-presets/${encodeURIComponent(presetId)}/update-preview`,
    "GET",
  );
}
