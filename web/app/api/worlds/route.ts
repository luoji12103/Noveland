import type { NextRequest } from "next/server";

import { proxyWorldRequest } from "@/lib/worlds/proxy";

export function GET(request: NextRequest): Promise<Response> {
  return proxyWorldRequest(request, [], "GET");
}

export function POST(request: NextRequest): Promise<Response> {
  return proxyWorldRequest(request, [], "POST");
}
