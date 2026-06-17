import type { NextRequest } from "next/server";

import { proxyEventStream } from "@/lib/realtime/proxy";

type ConversationStreamRouteProps = {
  params: Promise<{
    worldId: string;
    conversationId: string;
  }>;
};

export async function GET(
  request: NextRequest,
  { params }: ConversationStreamRouteProps,
): Promise<Response> {
  const { worldId, conversationId } = await params;
  return proxyEventStream(
    request,
    `/worlds/${encodeURIComponent(worldId)}/conversations/${encodeURIComponent(conversationId)}/stream`,
  );
}
