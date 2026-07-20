import { useEffect, useMemo, useRef, useState } from "react";
import { getDashboard, listAnalysisJobs } from "../api";
import LoadingState from "../components/LoadingState";
import ResetPrimaryRounds from "../components/ResetPrimaryRounds";
import StatusBadge from "../components/StatusBadge";
import { formatAnalysisJobLabel, jobContextLabel } from "../jobPresentation";
import type { DashboardData, DashboardFilters, Job } from "../types";

const dashboardFilterOrder: Array<keyof DashboardFilters> = ["order", "day", "time", "cluster", "course"];
const emptyFilters = (): DashboardFilters => ({ order: [], day: [], time: [], cluster: [], course: [] });
type FilterOption = { value: string; label: string };

function MultiSelectFilter({ label, values, options, onChange }: {
  label: string;
  values: string[];
  options: FilterOption[];
  onChange: (values: string[]) => void;
}) {
  const [search, setSearch] = useState("");
  const visibleOptions = options.filter((option) => option.label.toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR").trim()));
  const selectedLabel = values.length === 1
    ? options.find((option) => option.value === values[0])?.label ?? values[0]
    : values.length > 1 ? `${values.length} selecionados` : "Todos";
  const toggle = (value: string) => {
    onChange(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  };
  return (
    <fieldset className="multi-filter">
      <legend>{label}</legend>
      <details>
        <summary><span>{selectedLabel}</span><small>{values.length ? `${values.length}/${options.length}` : "Sem restrição"}</small></summary>
        <div className="multi-filter-menu" role="group" aria-label={`Opções de ${label}`}>
          {options.length > 7 && <label className="multi-filter-search"><span className="sr-only">Buscar em {label}</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Buscar ${label.toLocaleLowerCase("pt-BR")}`} /></label>}
          <button type="button" className="multi-filter-clear" disabled={!values.length} onClick={() => onChange([])}>Todos, sem restrição</button>
          <div className="multi-filter-options">
            {visibleOptions.length === 0 && <p className="multi-filter-empty">Nenhuma opção encontrada.</p>}
            {visibleOptions.map((option) => (
              <label key={option.value}>
                <input type="checkbox" checked={values.includes(option.value)} onChange={() => toggle(option.value)} />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>
      </details>
    </fieldset>
  );
}

function labelReason(reason: string) {
  const businessLabels: Record<string, string> = {
    SEM_CANDIDATO: "Sem docente elegível",
    SEM_DOCENTE_COM_PERFIL_E_CARGA: "Sem docente com perfil e carga disponível",
    CHOQUE_DE_HORARIO: "Conflito de agenda",
    CAPACIDADE_LETIVA_ESGOTADA: "Capacidade letiva esgotada",
    CAPACIDADE_E_HORARIO_COMBINADOS: "Capacidade e agenda indisponíveis",
    NAO_INFORMADO: "Motivo não informado",
    "NÃO INFORMADO": "Motivo não informado",
  };
  return businessLabels[reason.toLocaleUpperCase("pt-BR")] ?? reason.replaceAll("_", " ").toLocaleLowerCase("pt-BR");
}

function DeltaValue({ value }: { value: number }) {
  const state = value > 0 ? "deficit" : "surplus";
  return <strong className={state}>{value > 0 ? "+" : ""}{value.toFixed(0)}h</strong>;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState("");
  const [filters, setFilters] = useState<DashboardFilters>(emptyFilters);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const dashboardRequest = useRef(0);

  useEffect(() => {
    let active = true;
    void listAnalysisJobs()
      .then((items) => {
        if (!active) return;
        const complete = items.filter((item) => item.status === "CONCLUIDA");
        setJobs(complete);
        if (complete[0]) setSelected(complete[0].id);
      })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setJobsLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selected) {
      setDashboard(null);
      setLoading(false);
      return;
    }
    const requestId = ++dashboardRequest.current;
    let active = true;
    setLoading(true);
    setDashboard(null);
    setError("");
    const timer = window.setTimeout(() => {
      void getDashboard(selected, filters)
        .then((payload) => { if (active && requestId === dashboardRequest.current) setDashboard(payload); })
        .catch((requestError: Error) => { if (active && requestId === dashboardRequest.current) setError(requestError.message); })
        .finally(() => { if (active && requestId === dashboardRequest.current) setLoading(false); });
    }, 100);
    return () => { active = false; window.clearTimeout(timer); };
  }, [selected, filters]);

  const maxReason = useMemo(
    () => Math.max(1, ...(dashboard?.unassigned_reasons.map((item) => item.count) ?? [1])),
    [dashboard],
  );
  const maxDay = useMemo(
    () => Math.max(1, ...(dashboard?.charts.by_day.flatMap((item) => [item.disciplines, item.teachers]) ?? [1])),
    [dashboard],
  );
  const options = dashboard?.filters.options;
  const clusterTotal = useMemo(
    () => dashboard?.charts.demand_hours_by_cluster.reduce((total, item) => total + item.hours, 0) ?? 0,
    [dashboard],
  );
  const clusterBars = useMemo(() => {
    return [...(dashboard?.charts.demand_hours_by_cluster ?? [])].sort((a, b) => b.hours - a.hours || a.cluster.localeCompare(b.cluster, "pt-BR"));
  }, [dashboard]);
  const maxClusterHours = Math.max(1, ...clusterBars.map((item) => item.hours));
  const selectedJob = jobs.find((item) => item.id === selected) ?? null;
  const stageCoverage = dashboard ? [
    {
      label: "Primeiras 5 semanas",
      demand: dashboard.kpis.first_stage_demand_hours,
      covered: dashboard.stage_hours.first_stage ?? 0,
    },
    {
      label: "Últimas 5 semanas",
      demand: dashboard.kpis.second_stage_demand_hours,
      covered: dashboard.stage_hours.second_stage ?? 0,
    },
  ] : [];

  const updateFilter = (key: keyof DashboardFilters, values: string[]) => {
    setFilters((current) => ({ ...current, [key]: values }));
  };
  const hasFilters = Object.values(filters).some((values) => values.length > 0);
  const filterLabels: Record<keyof DashboardFilters, string> = { order: "Ordem", course: "Curso", cluster: "Cluster", day: "Dia", time: "Horário" };
  const optionMaps: Record<keyof DashboardFilters, FilterOption[]> = {
    order: options?.orders.map((value) => ({ value, label: value })) ?? [],
    course: options?.courses ?? [],
    cluster: options?.clusters.map((value) => ({ value, label: value })) ?? [],
    day: options?.days.map((value) => ({ value, label: value })) ?? [],
    time: options?.times.map((value) => ({ value, label: value })) ?? [],
  };
  const activeChips = dashboardFilterOrder.flatMap((key) =>
    filters[key].map((value) => ({ key, value, label: optionMaps[key].find((item) => item.value === value)?.label ?? value })),
  );

  return (
    <div className="page-container dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Visão gerencial</p>
          <h1>Dashboard da alocação</h1>
          <p>Monitore cobertura, demanda, capacidade docente e os principais direcionadores da rodada.</p>
        </div>
        <div className="page-heading-actions">
          <label className="compact-field">
            <span>Rodada analisada</span>
            <select value={selected} onChange={(event) => { setSelected(event.target.value); setFilters(emptyFilters()); }}>
              {jobs.length === 0 && <option value="">Nenhuma rodada concluída</option>}
              {jobs.map((job) => <option key={job.id} value={job.id}>{formatAnalysisJobLabel(job)}</option>)}
            </select>
          </label>
          <ResetPrimaryRounds disabled={!jobs.some((job) => job.kind === "PRIMARY")} />
        </div>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}
      {(jobsLoading || loading) && !dashboard && !error && (
        <LoadingState
          title={jobsLoading ? "Localizando rodadas auditadas" : "Atualizando a visão gerencial"}
          description={jobsLoading ? "Aguarde enquanto o histórico disponível é carregado." : "Indicadores e gráficos estão sendo recalculados para o recorte selecionado."}
        />
      )}
      {!jobsLoading && !loading && !dashboard && !error && (
        <section className="empty-state panel">
          <span aria-hidden="true">▥</span><h2>Execute uma rodada para liberar o dashboard</h2>
          <p>Os gráficos usam somente artefatos publicados e auditados pela aplicação.</p>
          <a className="button primary" href="#/processamento">Ir para processamento</a>
        </section>
      )}

      {dashboard && (
        <div className={`dashboard-workspace ${loading ? "is-refreshing" : ""}`} aria-busy={loading}>
          <aside className="filter-sidebar panel" aria-label="Filtros globais do dashboard">
            <div className="filter-heading"><div><span className="step-kicker">FILTROS</span><h2>Recorte da análise</h2></div>{loading && <><span className="mini-spinner" aria-hidden="true" /><span className="sr-only" role="status">Atualizando indicadores</span></>}</div>
            <p>Combine várias opções. Dentro de cada filtro vale “OU”; entre filtros vale “E”.</p>
            {dashboardFilterOrder.map((key) => <MultiSelectFilter key={key} label={filterLabels[key]} values={filters[key]} options={optionMaps[key]} onChange={(values) => updateFilter(key, values)} />)}
            <button className="button secondary" disabled={!hasFilters} onClick={() => setFilters(emptyFilters())}>Limpar filtros</button>
            <div className="filter-footnote"><strong>{dashboard.kpis.transmissions}</strong><span>ofertas no recorte atual</span></div>
          </aside>

          <div className="dashboard-content">
            <section className="confidence-strip" aria-label="Indicadores de confiança">
              <span>Validação <StatusBadge value={dashboard.guardrails.validation} /></span>
              <span>Solver <StatusBadge value={dashboard.guardrails.solver} /></span>
              <span>Auditoria <StatusBadge value={dashboard.guardrails.audit} /></span>
              <span>Rodada <strong>{dashboard.job.round}</strong></span>
              <span>Contexto <StatusBadge value={dashboard.job.is_official ? "APROVADO" : "EXECUTANDO"} label={jobContextLabel(dashboard.job)} /></span>
            </section>

            {hasFilters && <section className="active-filter-strip" aria-label="Filtros ativos" aria-live="polite"><strong>Recorte ativo</strong><div>{activeChips.map((chip) => <button type="button" key={`${chip.key}-${chip.value}`} onClick={() => updateFilter(chip.key, filters[chip.key].filter((value) => value !== chip.value))} title={`Remover ${filterLabels[chip.key]}: ${chip.label}`}><span>{filterLabels[chip.key]}</span>{chip.label}<b aria-hidden="true">×</b></button>)}</div><button type="button" className="clear-all" onClick={() => setFilters(emptyFilters())}>Limpar tudo</button></section>}

            <section className="kpi-grid dashboard-kpis">
              <article className={`kpi-card featured ${dashboard.kpis.coverage_pct >= 90 ? "tone-success" : "tone-warning"}`}><span>Taxa de cobertura</span><strong>{dashboard.kpis.coverage_pct.toFixed(2)}%</strong><small>{dashboard.kpis.allocated} de {dashboard.kpis.transmissions} ofertas</small></article>
              <article className={`kpi-card ${dashboard.kpis.unassigned ? "tone-warning" : "tone-success"}`}><span>Não alocadas</span><strong>{dashboard.kpis.unassigned}</strong><small>{dashboard.kpis.transmissions ? (100 - dashboard.kpis.coverage_pct).toFixed(2) : "0.00"}% do recorte</small></article>
              <article className="kpi-card tone-info"><span>Docentes ativos utilizados</span><strong>{dashboard.kpis.teacher_use_pct.toFixed(2)}%</strong><small>{dashboard.kpis.used_teachers} de {dashboard.kpis.active_teachers} ativos</small></article>
              <article className="kpi-card tone-neutral"><span>Ativos fora do recorte</span><strong>{dashboard.kpis.zero_active_teachers}</strong><small>sem oferta alocada neste recorte</small></article>
              <article className="kpi-card order-kpi tone-neutral"><span>Disciplinas por ordem</span><div className="order-values"><b>1ª <em>{dashboard.kpis.disciplines_by_order.first}</em></b><b>2ª <em>{dashboard.kpis.disciplines_by_order.second}</em></b><b>Estendida <em>{dashboard.kpis.disciplines_by_order.extended}</em></b></div><small>linhas de oferta do mapa</small></article>
              <article className="kpi-card tone-info"><span>Demanda · primeiras 5 semanas</span><strong>{dashboard.kpis.first_stage_demand_hours.toFixed(0)}h</strong><small>1ª + estendida</small></article>
              <article className="kpi-card tone-info"><span>Demanda · últimas 5 semanas</span><strong>{dashboard.kpis.second_stage_demand_hours.toFixed(0)}h</strong><small>2ª + estendida</small></article>
              <article className={`kpi-card delta-kpi ${dashboard.kpis.first_stage_capacity_delta_hours > 0 ? "tone-critical" : "tone-info"}`}><span>Delta CH · primeiras 5 semanas</span><DeltaValue value={dashboard.kpis.first_stage_capacity_delta_hours} /><small>demanda − CH letiva ativa</small></article>
              <article className={`kpi-card delta-kpi ${dashboard.kpis.second_stage_capacity_delta_hours > 0 ? "tone-critical" : "tone-info"}`}><span>Delta CH · últimas 5 semanas</span><DeltaValue value={dashboard.kpis.second_stage_capacity_delta_hours} /><small>demanda − CH letiva ativa</small></article>
            </section>

            <div className="dashboard-charts">
              <section className="panel chart-panel day-panel">
                <div className="section-title"><div><span className="step-kicker">AGENDA</span><h2>Disciplinas e professores por dia</h2><p>Ofertas demandadas e docentes únicos efetivamente alocados.</p></div></div>
                <div className="chart-legend"><span><i className="disciplines" />Disciplinas</span><span><i className="teachers" />Professores</span></div>
                <div className="day-chart" role="img" aria-label={`Disciplinas e professores por dia: ${dashboard.charts.by_day.map((item) => `${item.day}, ${item.disciplines} disciplinas e ${item.teachers} professores`).join("; ")}`}>
                  {dashboard.charts.by_day.map((item) => (
                    <div className="day-group" key={item.day}>
                      <div className="day-bars"><span className="disciplines" style={{ height: `${(100 * item.disciplines) / maxDay}%` }} data-value={item.disciplines} /><span className="teachers" style={{ height: `${(100 * item.teachers) / maxDay}%` }} data-value={item.teachers} /></div>
                      <strong>{item.day.slice(0, 3)}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel chart-panel cluster-panel">
                <div className="section-title"><div><span className="step-kicker">COMPOSIÇÃO</span><h2>Horas demandadas por cluster</h2><p>Todos os clusters, ordenados por demanda. Total do recorte: {clusterTotal}h.</p></div></div>
                <div className="cluster-ranked-bars" role="list" aria-label={`Demanda de ${clusterBars.length} clusters, total ${clusterTotal} horas`}>
                  {clusterBars.length ? clusterBars.map((item) => {
                    const share = clusterTotal ? (100 * item.hours) / clusterTotal : 0;
                    return <div className="cluster-bar-row" role="listitem" aria-label={`${item.cluster}: ${item.hours} horas, ${share.toFixed(1)}% da demanda`} key={item.cluster}><div><strong>{item.cluster}</strong><span>{item.hours}h · {share.toFixed(1)}%</span></div><div className="cluster-bar-track" aria-hidden="true"><span style={{ width: `${(100 * item.hours) / maxClusterHours}%` }} /></div></div>;
                  }) : <div className="chart-empty" role="listitem">Nenhum cluster no recorte atual.</div>}
                </div>
              </section>

              <section className="panel chart-panel">
                <div className="section-title"><div><span className="step-kicker">DIAGNÓSTICO</span><h2>Motivos das não alocadas</h2><p>Restrições que impedem a cobertura no recorte.</p></div></div>
                {dashboard.unassigned_reasons.length ? <div className="bar-chart constraint-bars">{dashboard.unassigned_reasons.map((item) => <div className="bar-row" key={item.reason}><div><span>{labelReason(item.reason)}</span><strong>{item.count}</strong></div><div className="bar-track"><span style={{ width: `${(100 * item.count) / maxReason}%` }} /></div></div>)}</div> : <div className="chart-empty state-success">Nenhuma oferta sem alocação neste recorte.</div>}
              </section>

              <section className="panel chart-panel">
                <div className="section-title"><div><span className="step-kicker">CAPACIDADE ALOCADA</span><h2>Horas cobertas por etapa</h2><p>Somente ofertas com docente definido.</p></div></div>
                <div className="stage-coverage-list">
                  {stageCoverage.map((stage) => {
                    const balance = stage.covered - stage.demand;
                    const coveredPct = stage.demand ? Math.min(100, (100 * stage.covered) / stage.demand) : 0;
                    return <div className="stage-coverage-row" key={stage.label}><div className="stage-coverage-heading"><strong>{stage.label}</strong><span className={balance >= 0 ? "is-covered" : "has-gap"}>{balance > 0 ? "+" : ""}{balance.toFixed(0)}h de saldo</span></div><div className="stage-coverage-values"><span>Demanda <b>{stage.demand.toFixed(0)}h</b></span><span>Cobertura <b>{stage.covered.toFixed(0)}h</b></span></div><div className="stage-coverage-track" role="img" aria-label={`${stage.label}: ${stage.covered.toFixed(0)} de ${stage.demand.toFixed(0)} horas cobertas, saldo ${balance.toFixed(0)} horas`}><span style={{ width: `${coveredPct}%` }} /></div></div>;
                  })}
                </div>
                <p className="chart-note">{dashboard.metric_notes.demand}</p>
              </section>
            </div>

            <footer className="source-note"><span>Fonte</span>{dashboard.source_note}<br />{dashboard.metric_notes.capacity_delta}{selectedJob && <> Contexto selecionado: {jobContextLabel(selectedJob)}.</>}<a className="inline-link" href="#/insights">Explorar oportunidades →</a></footer>
          </div>
        </div>
      )}
    </div>
  );
}
