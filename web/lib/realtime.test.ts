import { afterEach, describe, expect, it, vi } from "vitest";

import { createConversationLiveSocket } from "@/lib/realtime";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readonly listeners = new Map<string, EventListener[]>();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener): void {
    const existing = this.listeners.get(type) ?? [];
    existing.push(listener);
    this.listeners.set(type, existing);
  }
}

describe("realtime client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    MockWebSocket.instances = [];
  });

  it("encodes conversation live WebSocket path segments", () => {
    vi.stubEnv("NEXT_PUBLIC_NOVELAND_API_WS_BASE_URL", "ws://api.example.test///");
    vi.stubGlobal("WebSocket", MockWebSocket);

    createConversationLiveSocket("world/admin", "conversation/debug?x=1#frag");

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0]?.url).toBe(
      "ws://api.example.test/worlds/world%2Fadmin/conversations/conversation%2Fdebug%3Fx%3D1%23frag/live",
    );
  });

  it("wires live socket handlers", () => {
    vi.stubGlobal("WebSocket", MockWebSocket);
    const handlers = {
      onOpen: vi.fn(),
      onMessage: vi.fn(),
      onError: vi.fn(),
      onClose: vi.fn(),
    };

    createConversationLiveSocket("world-1", "conversation-1", handlers);

    const socket = MockWebSocket.instances[0];
    expect(socket?.listeners.get("open")).toHaveLength(1);
    expect(socket?.listeners.get("message")).toHaveLength(1);
    expect(socket?.listeners.get("error")).toHaveLength(1);
    expect(socket?.listeners.get("close")).toHaveLength(1);
  });
});
