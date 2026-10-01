import { Droplet } from "lucide-react";
import { useRoute } from "./router";
import { STEPS, STEP_BY_ID } from "./steps";
import { VentasPage } from "./pages/VentasPage";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AutoescaladoPage } from "./pages/AutoescaladoPage";

export function App() {
  const [route, navigate] = useRoute();
  const step = STEP_BY_ID[route];

  return (
    <div className="min-h-full">
      <header className="border-b border-ink-border bg-ink-800/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1800px] flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-cyan/15 text-accent-cyan">
              <Droplet size={20} />
            </span>
            <div>
              <h1 className="text-lg font-bold text-white">
                Refrescos LATAM
              </h1>
              <p className="text-xs text-gray-400">
                Ventas en tiempo real, IA, y análisis HTAP
              </p>
            </div>
          </div>

          {/* 4-step narrative stepper */}
          <nav className="flex flex-wrap items-center gap-1 rounded-lg border border-ink-border bg-ink-700 p-1">
            {STEPS.map((s) => {
              const active = route === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => navigate(s.id)}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                    active
                      ? "bg-accent-cyan text-black"
                      : "text-gray-300 hover:bg-ink-600"
                  }`}
                >
                  {s.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Step caption bar */}
      <div className="border-b border-ink-border bg-ink-900/60">
        <div className="mx-auto flex max-w-[1800px] items-center gap-2 px-4 py-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent-cyan/20 text-[11px] font-bold text-accent-cyan">
            {step.n}
          </span>
          <span className="text-sm font-semibold text-white">{step.title}</span>
          <span className="text-xs text-gray-400">— {step.caption}</span>
        </div>
      </div>

      <main className="mx-auto max-w-[1800px]">
        {route === "ventas" && <VentasPage key="ventas" />}
        {route === "chat" && <ChatPage key="chat" />}
        {route === "dashboard" && <DashboardPage key="dashboard" />}
        {route === "autoescalado" && <AutoescaladoPage key="autoescalado" />}
      </main>
    </div>
  );
}
