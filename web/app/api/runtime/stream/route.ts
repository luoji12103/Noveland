import type { NextRequest } from "next/server";

import { proxyEventStream } from "@/lib/realtime/proxy";

export async function GET(request: NextRequest): Promise<Response> {
  return proxyEventStream(request, "/runtime/stream");
}
