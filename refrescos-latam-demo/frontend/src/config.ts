// Frontend config. iframe embed URLs can be injected at runtime by the server
// (window.__LTAP_CONFIG__) or fall back to build-time Vite env, then empty.
// Empty => the panel renders a "not configured yet" placeholder.

declare global {
  interface Window {
    __LTAP_CONFIG__?: {
      aibiDashboardUrl?: string;
      genieSpaceUrl?: string;
    };
  }
}

const injected = typeof window !== "undefined" ? window.__LTAP_CONFIG__ : undefined;

export const config = {
  aibiDashboardUrl:
    injected?.aibiDashboardUrl ??
    (import.meta.env.VITE_AIBI_DASHBOARD_URL as string | undefined) ??
    "",
  genieSpaceUrl:
    injected?.genieSpaceUrl ??
    (import.meta.env.VITE_GENIE_SPACE_URL as string | undefined) ??
    "",
};
