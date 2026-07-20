import { useEffect, useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import ProcessPage from "./pages/ProcessPage";
import ScenariosPage from "./pages/ScenariosPage";
import InsightsPage from "./pages/InsightsPage";

type Route = "processamento" | "dashboard" | "insights" | "cenarios";

function currentRoute(): Route {
  const route = window.location.hash.replace("#/", "") as Route;
  return ["processamento", "dashboard", "insights", "cenarios"].includes(route)
    ? route
    : "processamento";
}

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) window.location.hash = "#/processamento";
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Ir para o conteúdo principal</a>
      <header className="topbar">
        <div className="brand-wordmark" aria-label="UniCesumar">UniCesumar</div>
        <span className="brand-divider" aria-hidden="true" />
        <div className="brand-copy">
          <strong>Alocação Docente</strong>
          <span>Inteligência para o planejamento acadêmico</span>
        </div>
        <div className="environment-badge">BETA</div>
      </header>

      <nav className="main-nav" aria-label="Módulos da aplicação">
        <a className={route === "processamento" ? "active" : ""} aria-current={route === "processamento" ? "page" : undefined} href="#/processamento">
          <span className="nav-number">01</span>
          Processamento
        </a>
        <a className={route === "dashboard" ? "active" : ""} aria-current={route === "dashboard" ? "page" : undefined} href="#/dashboard">
          <span className="nav-number">02</span>
          Dashboard
        </a>
        <a className={route === "insights" ? "active" : ""} aria-current={route === "insights" ? "page" : undefined} href="#/insights">
          <span className="nav-number">03</span>
          Insights
        </a>
        <a className={route === "cenarios" ? "active" : ""} aria-current={route === "cenarios" ? "page" : undefined} href="#/cenarios">
          <span className="nav-number">04</span>
          Cenários
        </a>
      </nav>

      <main id="main-content" tabIndex={-1}>
        {route === "processamento" && <ProcessPage />}
        {route === "dashboard" && <DashboardPage />}
        {route === "insights" && <InsightsPage />}
        {route === "cenarios" && <ScenariosPage />}
      </main>
    </div>
  );
}
