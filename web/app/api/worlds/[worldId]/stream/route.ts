import type { NextRequest } from "next/server";

import { proxyEventStream } from "@/lib/realtime/proxy";

type WorldStreamRouteProps = {
  params: Promise<{
    worldId: string;
  }>;
};

export async function GET(
  request: NextRequest,
  { params }: WorldStreamRouteProps,
): Promise<Response> {
  const { worldId } = await params;
  return proxyEventStream(request, `/worlds/${encodeURIComponent(worldId)}/stream`);
}
