import { useEffect, useState } from "react";
import { Bot, Send, User, Wrench, Database, RefreshCw, Braces, Trash2 } from "lucide-react";
import { api, type AgentInsertResp, type MemoryTurn } from "../api";
import { Card } from "../components/Card";
import { ComputeBadge } from "../components/ComputeBadge";
import { createStore } from "../store";

interface Turn {
  message: string;
  resp?: AgentInsertResp;
  error?: string;
  pending?: boolean;
}

// Example prompts for the agent (in Spanish, about sodas)
const EXAMPLES = [
  "vende 3 cajas de Inca Kola en Lima",
  "registra 2 botellas de Coca-Cola en México",
  "una venta de 5 Fanta Naranja en Santiago",
];

// Persistent thread state in localStorage
const threadStore = createStore<{ threadId: string }>({
  threadId: crypto.randomUUID(),
});

// Tab 2 — Chat con agente. LLM agent chat + memory panel.
export function ChatPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [memory, setMemory] = useState<MemoryTurn[]>([]);
  const [threadId, setThreadId] = useState(threadStore.getState().threadId);

  const loadMemory = () =>
    api
      .agentMemory(threadId)
      .then((m) => {
        setMemory(m.turns);
      })
      .catch(() => {});

  // Clear memory and start fresh thread
  const clearMemory = async () => {
    try {
      await api.clearAgentMemory(threadId);
      const newThreadId = crypto.randomUUID();
      threadStore.setState({ threadId: newThreadId });
      setThreadId(newThreadId);
      setTurns([]);
      setMemory([]);
    } catch {
      /* ignore */
    }
  };

  // Load memory on mount and when threadId changes
  useEffect(() => {
    loadMemory();
  }, [threadId]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { message, pending: true }]);
    try {
      const resp = await api.agentInsert(message, threadId);
      setTurns((t) =>
        t.map((turn, i) =>
          i === t.length - 1 ? { message, resp, pending: false } : turn,
        ),
      );
      await loadMemory();
    } catch (e) {
      const error = e instanceof Error ? e.message : "Error del agente";
      setTurns((t) =>
        t.map((turn, i) =>
          i === t.length - 1 ? { message, error, pending: false } : turn,
        ),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-1 gap-3 p-3 lg:grid-cols-2">
      {/* LEFT: agentic chat */}
      <div className="scroll-panel min-h-0 overflow-y-auto pr-1">
        <Card title="Chat con agente" badge={<ComputeBadge kind="agent" />}>
          <div className="flex items-center gap-2 text-gray-400">
            <Bot size={14} />
            <span className="text-xs">
              El agente interpreta lenguaje natural para registrar ventas.
            </span>
          </div>

          {/* Example prompts */}
          <div className="mt-3 flex flex-col gap-1.5">
            <span className="text-[11px] uppercase tracking-wide text-gray-500">
              Ejemplos (clic para enviar)
            </span>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => send(ex)}
                  title="Clic para enviar"
                  className="rounded-full border border-ink-border bg-ink-800/60 px-3 py-1.5 text-xs text-gray-300 transition hover:border-accent-purple/50 hover:text-accent-purple"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation */}
          <div className="mt-4 flex flex-col gap-4">
            {turns.map((turn, i) => (
              <div key={i} className="flex flex-col gap-2">
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink-600 text-gray-300">
                    <User size={13} />
                  </span>
                  <div className="rounded-lg rounded-tl-none bg-ink-600 px-3 py-2 text-sm text-gray-100">
                    {turn.message}
                  </div>
                </div>

                {turn.pending && (
                  <div className="ml-8 text-xs text-gray-500">El agente está pensando…</div>
                )}
                {turn.error && (
                  <div className="ml-8 rounded-lg border border-accent-red/40 bg-accent-red/10 px-3 py-2 text-xs text-accent-red">
                    {turn.error}
                  </div>
                )}

                {turn.resp && (
                  <div className="ml-8 flex flex-col gap-2">
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-purple/20 text-accent-purple">
                        <Bot size={13} />
                      </span>
                      <div className="rounded-lg rounded-tl-none border border-accent-purple/20 bg-accent-purple/5 px-3 py-2 text-sm text-gray-200">
                        {turn.resp.reasoning}
                      </div>
                    </div>

                    {/* Show tool call if registered */}
                    {turn.resp.registered && turn.resp.tool_call && (
                      <div className="rounded-lg border border-ink-border bg-ink-900 p-3">
                        <div className="mb-1.5 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-gray-400">
                          <Wrench size={12} /> Herramienta ejecutada
                        </div>
                        <pre className="overflow-x-auto text-xs leading-relaxed text-accent-purple">
                          <code>
                            {turn.resp.tool_call.name}
                            ({JSON.stringify(turn.resp.tool_call.arguments)})
                          </code>
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="mt-4 flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Describe la venta en lenguaje natural…"
              className="flex-1 rounded-lg border border-ink-border bg-ink-900 px-3 py-2.5 text-sm text-gray-100 outline-none transition focus:border-accent-purple"
            />
            <button
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-accent-purple px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-40"
            >
              <Send size={16} /> Enviar
            </button>
          </div>
        </Card>
      </div>

      {/* RIGHT: agent memory persisted in Lakebase */}
      <div className="scroll-panel min-h-0 overflow-y-auto pr-1">
        <Card
          title="Memoria del agente en Lakebase"
          badge={<ComputeBadge kind="lakebase" short />}
        >
          <div className="flex items-center justify-between gap-2 text-gray-400">
            <div className="flex items-center gap-2">
              <Database size={14} />
              <span className="text-xs">
                Conversación guardada en Postgres (checkpointing por{" "}
                <code className="text-accent-cyan">thread_id</code>).
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <button
                onClick={loadMemory}
                title="Releer memoria desde Lakebase"
                className="rounded-md border border-ink-border bg-ink-800/60 p-1.5 text-gray-400 transition hover:text-accent-cyan"
              >
                <RefreshCw size={13} />
              </button>
              <button
                onClick={clearMemory}
                title="Nueva conversación"
                className="rounded-md border border-ink-border bg-ink-800/60 p-1.5 text-gray-400 transition hover:text-accent-red"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2 text-[11px] text-gray-500">
            <span className="rounded-full border border-ink-border bg-ink-900 px-2 py-0.5 font-mono">
              thread_id: {threadId.slice(0, 8)}…
            </span>
            <span>· {memory.length} turnos</span>
          </div>

          {memory.length === 0 ? (
            <div className="mt-3 rounded-lg border border-dashed border-ink-border bg-ink-900/60 px-3 py-8 text-center text-xs text-gray-500">
              Envía un mensaje al agente para ver cómo su conversación se guarda en
              Lakebase.
            </div>
          ) : (
            <div className="mt-3 flex flex-col gap-2">
              {memory.map((t) => (
                <div
                  key={t.turn_idx}
                  className="rounded-lg border border-ink-border bg-ink-900 p-2.5"
                >
                  <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-gray-500">
                    <span className="tnum rounded bg-ink-700 px-1.5 py-0.5">
                      #{t.turn_idx}
                    </span>
                    <span
                      className={
                        t.role === "user" ? "text-gray-300" : "text-accent-purple"
                      }
                    >
                      {t.role === "user" ? "usuario" : "asistente"}
                    </span>
                  </div>
                  <div className="text-xs leading-relaxed text-gray-200">
                    {t.content}
                  </div>
                  {t.tool_call && (
                    <div className="mt-1.5 flex items-start gap-1.5 rounded bg-ink-800/70 px-2 py-1.5 text-[11px] text-accent-purple">
                      <Braces size={12} className="mt-0.5 shrink-0" />
                      <code className="break-all">
                        {t.tool_call.name}({JSON.stringify(t.tool_call.arguments)})
                      </code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
