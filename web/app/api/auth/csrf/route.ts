import type { NextRequest } from "next/server";

import { proxyAuthRequest } from "@/lib/auth/proxy";

export function GET(request: NextRequest): Promise<Response> {
  return proxyAuthRequest(request, "/auth/csrf", "GET");
}
