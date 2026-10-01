// Minimal hash router. `react-router-dom` was unavailable in the offline field
// environment, so this covers the four narrative steps the demo needs with
// hash-based navigation. Swap for react-router-dom when available.
import { useEffect, useState, type ReactNode } from "react";

// Refrescos LATAM: four steps for sales, chat, dashboard, and HTAP.
export type Route = "ventas" | "chat" | "dashboard" | "autoescalado";

const ROUTES: Route[] = ["ventas", "chat", "dashboard", "autoescalado"];

function parseHash(): Route {
  const h = window.location.hash.replace(/^#\/?/, "").toLowerCase();
  return (ROUTES as string[]).includes(h) ? (h as Route) : "ventas";
}

export function useRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(parseHash());

  useEffect(() => {
    // Default redirect to /ventas (step 1 of the narrative).
    if (!window.location.hash) window.location.hash = "#/ventas";
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = (r: Route) => {
    window.location.hash = `#/${r}`;
  };

  return [route, navigate];
}

export function Link({
  to,
  active,
  children,
  className,
}: {
  to: Route;
  active: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <a
      href={`#/${to}`}
      className={className}
      aria-current={active ? "page" : undefined}
    >
      {children}
    </a>
  );
}
