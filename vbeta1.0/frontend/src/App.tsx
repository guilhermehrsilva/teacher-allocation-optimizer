import { useEffect, useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import ProcessPage from "./pages/ProcessPage";
import ScenariosPage from "./pages/ScenariosPage";
import InsightsPage from "./pages/InsightsPage";
import ExportPage from "./pages/ExportPage";
import OptimalLogo from "./components/OptimalLogo";

type Route = "processamento" | "dashboard" | "insights" | "cenarios" | "exportacao";

const routeTitles: Record<Route, string> = {
  processamento: "Processamento",
  dashboard: "Dashboard",
  insights: "Insights",
  cenarios: "Cenários",
  exportacao: "Exportação",
};

function currentRoute(): Route {
  const route = window.location.hash.replace("#/", "") as Route;
  return ["processamento", "dashboard", "insights", "cenarios", "exportacao"].includes(route)
    ? route
    : "processamento";
}

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);

  useEffect(() => {
    const onHashChange = () => {
      setRoute(currentRoute());
      window.requestAnimationFrame(() => {
        document.getElementById("main-content")?.focus({ preventScroll: true });
      });
    };
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) window.location.hash = "#/processamento";
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    document.title = `${routeTitles[route]} · Alocação Docente`;
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [route]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Ir para o conteúdo principal</a>
      <header className="topbar">
        <OptimalLogo />
        <span className="brand-divider" aria-hidden="true" />
        <div className="brand-copy">
          <strong>Alocação Docente</strong>
          <span>Inteligência para o planejamento acadêmico</span>
        </div>
        <div className="header-meta">
          <div className="environment-badge">VERSÃO 1.0</div>
          <div className="developer-credit" aria-label="Créditos do autor">
            <span>Desenvolvido por</span>
            <strong>Guilherme Henrique Risson Silva</strong>
          </div>
        </div>
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
        <a className={route === "exportacao" ? "active" : ""} aria-current={route === "exportacao" ? "page" : undefined} href="#/exportacao">
          <span className="nav-number">05</span>
          Exportação
        </a>
      </nav>

      <main id="main-content" tabIndex={-1}>
        {route === "processamento" && <ProcessPage />}
        {route === "dashboard" && <DashboardPage />}
        {route === "insights" && <InsightsPage />}
        {route === "cenarios" && <ScenariosPage />}
        {route === "exportacao" && <ExportPage />}
      </main>
    </div>
  );
}
