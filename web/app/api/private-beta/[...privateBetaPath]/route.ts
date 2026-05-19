import type { NextRequest } from "next/server";

import { proxyPrivateBetaRequest } from "@/lib/private-beta/proxy";

type RouteContext = {
  params: Promise<{
    privateBetaPath: string[];
  }>;
};

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyPrivateBetaRequest(request, await pathSegments(context), "GET");
}

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyPrivateBetaRequest(request, await pathSegments(context), "POST");
}

async function pathSegments(context: RouteContext): Promise<string[]> {
  return (await context.params).privateBetaPath.map(encodeURIComponent);
}
