"use client";

import { getAuthApiWebSocketBaseUrl } from "@/lib/auth/server-config";
import type {
  ConversationStreamPayload,
  RuntimeStreamPayload,
  StreamEnvelope,
  WorldStreamPayload,
} from "@/lib/worlds/types";

export type RuntimeStreamEnvelope = StreamEnvelope<RuntimeStreamPayload>;
export type WorldStreamEnvelope = StreamEnvelope<WorldStreamPayload>;
export type ConversationStreamEnvelope = StreamEnvelope<ConversationStreamPayload>;

export type ConversationLiveCommand =
  | {
      command: "seed";
      request_id: string;
      payload: {
        input_text: string;
      };
    }
  | {
      command: "advance" | "start" | "pause" | "resume";
      request_id: string;
      payload: Record<string, never>;
    };

export type ConversationLiveMessage = {
  type: "ack" | "session_snapshot" | "turn_appended" | "status_changed" | "error";
  request_id?: string;
  occurred_at: string;
  payload: Record<string, unknown>;
};

export function subscribeToEventStream<TPayload>(
  path: string,
  onEnvelope: (envelope: StreamEnvelope<TPayload>) => void,
  onError?: () => void,
): () => void {
  const eventSource = new EventSource(path, { withCredentials: true });
  eventSource.onmessage = (event) => {
    const envelope = JSON.parse(event.data) as StreamEnvelope<TPayload>;
    onEnvelope(envelope);
  };
  eventSource.onerror = () => {
    onError?.();
  };
  return () => {
    eventSource.close();
  };
}

export function createConversationLiveSocket(
  worldId: string,
  conversationId: string,
  handlers: {
    onOpen?: () => void;
    onMessage?: (message: ConversationLiveMessage) => void;
    onError?: () => void;
    onClose?: () => void;
  } = {},
): WebSocket {
  const socket = new WebSocket(
    `${getAuthApiWebSocketBaseUrl()}/worlds/${encodeURIComponent(
      worldId,
    )}/conversations/${encodeURIComponent(conversationId)}/live`,
  );
  socket.addEventListener("open", () => {
    handlers.onOpen?.();
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data) as ConversationLiveMessage;
    handlers.onMessage?.(message);
  });
  socket.addEventListener("error", () => {
    handlers.onError?.();
  });
  socket.addEventListener("close", () => {
    handlers.onClose?.();
  });
  return socket;
}

export function nextRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function mergeById<T extends { id: string }>(current: T[], incoming: T[]): T[] {
  const byId = new Map(current.map((item) => [item.id, item]));
  for (const item of incoming) {
    byId.set(item.id, item);
  }
  return Array.from(byId.values());
}
