import type { NextRequest } from "next/server";

import { proxyRuntimeRequest } from "@/lib/runtime/proxy";

export function GET(request: NextRequest): Promise<Response> {
  return proxyRuntimeRequest(request, "/runtime/control", "GET");
}

export function PATCH(request: NextRequest): Promise<Response> {
  return proxyRuntimeRequest(request, "/runtime/control", "PATCH");
}
