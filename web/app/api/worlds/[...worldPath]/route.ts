import type { NextRequest } from "next/server";

import { proxyWorldRequest } from "@/lib/worlds/proxy";

type RouteContext = {
  params: Promise<{
    worldPath: string[];
  }>;
};

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyWorldRequest(request, await pathSegments(context), "GET");
}

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyWorldRequest(request, await pathSegments(context), "POST");
}

export async function PATCH(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyWorldRequest(request, await pathSegments(context), "PATCH");
}

export async function PUT(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyWorldRequest(request, await pathSegments(context), "PUT");
}

export async function DELETE(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyWorldRequest(request, await pathSegments(context), "DELETE");
}

async function pathSegments(context: RouteContext): Promise<string[]> {
  return (await context.params).worldPath.map(encodeURIComponent);
}
