import type { ReactElement } from "react";
import { AgentSessionPage } from "./pages/AgentSessionPage";
import { MerchantHomePage } from "./pages/MerchantHomePage";

export function App(): ReactElement {
  if (window.location.pathname.startsWith("/agent-session/")) {
    return <AgentSessionPage />;
  }
  return <MerchantHomePage />;
}
