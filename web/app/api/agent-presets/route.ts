import type { NextRequest } from "next/server";

import { proxyApiRequest } from "@/lib/api-proxy";

export async function GET(request: NextRequest): Promise<Response> {
  return proxyApiRequest(request, "/agent-presets", "GET");
}

export async function POST(request: NextRequest): Promise<Response> {
  return proxyApiRequest(request, "/agent-presets", "POST");
}
