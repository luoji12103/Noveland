import type { NextRequest } from "next/server";

import { proxyAuthRequest } from "@/lib/auth/proxy";

export function POST(request: NextRequest): Promise<Response> {
  return proxyAuthRequest(request, "/auth/login", "POST");
}
