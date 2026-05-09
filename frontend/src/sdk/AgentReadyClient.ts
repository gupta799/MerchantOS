import { backendBaseUrl } from "../api/http";
import type { BackendToBrowserMessage, BrowserToBackendMessage } from "./messages";
import { parseBackendMessage } from "./messages";
import { observeBrowser } from "./observe";
import { executeAction } from "./executeAction";
import { emitMerchantEvent } from "./events";

export type AgentReadyCallbacks = {
  onReady?: () => void;
  onAssistantUpdate: (message: string) => void;
  onTraceUpdate: () => void;
  onDone: (message: string) => void;
  onError: (message: string) => void;
};

export class AgentReadyClient {
  private socket: WebSocket | null = null;

  constructor(
    private readonly sessionId: string,
    private readonly root: HTMLElement,
    private readonly callbacks: AgentReadyCallbacks
  ) {}

  connect(): void {
    const wsBase = backendBaseUrl().replace("http://", "ws://").replace("https://", "wss://");
    this.socket = new WebSocket(`${wsBase}/api/sessions/${this.sessionId}/guide/ws`);
    this.socket.addEventListener("open", () => {
      void this.sendGuideReady().then(() => this.callbacks.onReady?.());
    });
    this.socket.addEventListener("message", (event: MessageEvent<string>) => {
      void this.handleMessage(parseBackendMessage(event.data));
    });
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
  }

  async emitGuidedSessionOpened(): Promise<void> {
    await emitMerchantEvent(this.sessionId, {
      type: "guided_session_opened",
      source: "merchant_sdk",
      message: "Customer opened a guided merchant session"
    });
  }

  private async sendGuideReady(): Promise<void> {
    const message: BrowserToBackendMessage = {
      type: "guide_ready",
      session_id: this.sessionId,
      observation: await observeBrowser(this.root)
    };
    this.send(message);
  }

  private async handleMessage(message: BackendToBrowserMessage): Promise<void> {
    if (message.type === "request_observation") {
      this.send({
        type: "observation",
        session_id: this.sessionId,
        observation: await observeBrowser(this.root)
      });
      return;
    }
    if (message.type === "execute_action") {
      const result = await executeAction(this.root, message.action);
      this.send({
        type: "action_result",
        session_id: this.sessionId,
        result
      });
      return;
    }
    if (message.type === "assistant_update") {
      this.callbacks.onAssistantUpdate(message.message);
      return;
    }
    if (message.type === "trace_update") {
      this.callbacks.onTraceUpdate();
      return;
    }
    if (message.type === "guide_done") {
      this.callbacks.onDone(message.message);
      return;
    }
    if (message.type === "guide_error") {
      this.callbacks.onError(message.message);
    }
  }

  private send(message: BrowserToBackendMessage): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }
}
