import { useEffect, useMemo, useState } from "react";
import { getDashboard, listAnalysisJobs } from "../api";
import ResetPrimaryRounds from "../components/ResetPrimaryRounds";
import type { DashboardData, DashboardFilters, Job } from "../types";

const dashboardFilterOrder: Array<keyof DashboardFilters> = ["order", "day", "time", "cluster", "course"];
const emptyFilters = (): DashboardFilters => ({ order: [], day: [], time: [], cluster: [], course: [] });
const clusterColors = [
  "#247a9a", "#6a78a8", "#7c6f9d", "#9a6f8c", "#ad6f6b", "#b77d52", "#b08b3e",
  "#8c9651", "#64906b", "#438b7c", "#3c8793", "#5d7f91", "#7c8790", "#8a7566",
  "#9b8056", "#6c8f9f", "#8278a6", "#a1769a", "#a96e54", "#758d5d",
];

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
  return reason.replaceAll("_", " ").toLocaleLowerCase("pt-BR");
}

function labelState(state: string) {
  return state.replaceAll("_", " ");
}

function stateTone(state: string) {
  const normalized = state.toLocaleUpperCase("pt-BR");
  if (["APROVADO", "OPTIMAL", "CONCLUIDA"].includes(normalized)) return "is-success";
  if (["APROVADO_COM_RESSALVAS", "FEASIBLE"].includes(normalized)) return "is-warning";
  if (["REPROVADO", "FAILED", "INFEASIBLE"].includes(normalized)) return "is-critical";
  return "is-info";
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void listAnalysisJobs()
      .then((items) => {
        const complete = items.filter((item) => item.status === "CONCLUIDA");
        setJobs(complete);
        if (complete[0]) setSelected(complete[0].id);
      })
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      void getDashboard(selected, filters)
        .then((payload) => { if (active) setDashboard(payload); })
        .catch((requestError: Error) => { if (active) setError(requestError.message); })
        .finally(() => { if (active) setLoading(false); });
    }, dashboard ? 140 : 0);
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
  const clusterColorMap = useMemo(() => new Map(
    (options?.clusters ?? []).map((cluster, index) => [cluster, clusterColors[index % clusterColors.length]]),
  ), [options?.clusters]);
  const clusterColor = (cluster: string) => clusterColorMap.get(cluster) ?? "#75787b";
  const clusterTotal = useMemo(
    () => dashboard?.charts.demand_hours_by_cluster.reduce((total, item) => total + item.hours, 0) ?? 0,
    [dashboard],
  );
  const clusterLegendRows = useMemo(() => {
    const items = dashboard?.charts.demand_hours_by_cluster ?? [];
    const midpoint = Math.ceil(items.length / 2);
    return [items.slice(0, midpoint), items.slice(midpoint)].filter((row) => row.length > 0);
  }, [dashboard]);
  const donutBackground = useMemo(() => {
    let cursor = 0;
    const stops = dashboard?.charts.demand_hours_by_cluster.map((item) => {
      const start = cursor;
      cursor += clusterTotal ? (100 * item.hours) / clusterTotal : 0;
      return `${clusterColor(item.cluster)} ${start}% ${cursor}%`;
    }) ?? [];
    return `conic-gradient(${stops.join(", ") || "#d9e1e2 0 100%"})`;
  }, [dashboard, clusterTotal, clusterColorMap]);

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
              {jobs.map((job) => <option key={job.id} value={job.id}>{job.round} · {job.filename}</option>)}
            </select>
          </label>
          <ResetPrimaryRounds disabled={!jobs.some((job) => job.kind === "PRIMARY")} />
        </div>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}
      {!dashboard && !error && (
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
              <span>Validação <strong className={stateTone(dashboard.guardrails.validation)}>{labelState(dashboard.guardrails.validation)}</strong></span>
              <span>Solver <strong className={stateTone(dashboard.guardrails.solver)}>{labelState(dashboard.guardrails.solver)}</strong></span>
              <span>Auditoria <strong className={stateTone(dashboard.guardrails.audit)}>{labelState(dashboard.guardrails.audit)}</strong></span>
              <span>Rodada <strong>{dashboard.job.round}</strong></span>
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
                <div className="day-chart" role="img" aria-label="Quantidade de disciplinas e professores por dia da semana">
                  {dashboard.charts.by_day.map((item) => (
                    <div className="day-group" key={item.day}>
                      <div className="day-bars"><span className="disciplines" style={{ height: `${(100 * item.disciplines) / maxDay}%` }} data-value={item.disciplines} /><span className="teachers" style={{ height: `${(100 * item.teachers) / maxDay}%` }} data-value={item.teachers} /></div>
                      <strong>{item.day.slice(0, 3)}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel chart-panel donut-panel">
                <div className="section-title"><div><span className="step-kicker">COMPOSIÇÃO</span><h2>Horas demandadas por cluster</h2><p>Participação na demanda filtrada.</p></div></div>
                <div className="donut-legend">
                  {clusterLegendRows.map((row, rowIndex) => <div className="donut-legend-row" key={rowIndex}>{row.map((item) => <div key={item.cluster}><i style={{ background: clusterColor(item.cluster) }} /><span>{item.cluster}</span><strong>{item.hours}h <small>{clusterTotal ? ((100 * item.hours) / clusterTotal).toFixed(1) : "0.0"}%</small></strong></div>)}</div>)}
                </div>
                <div className="donut-layout">
                  <div className="donut-chart" style={{ background: donutBackground }} role="img" aria-label={`Horas demandadas por cluster, total ${clusterTotal} horas`}><div><strong>{clusterTotal}h</strong><span>demanda</span></div></div>
                </div>
              </section>

              <section className="panel chart-panel">
                <div className="section-title"><div><span className="step-kicker">DIAGNÓSTICO</span><h2>Motivos das não alocadas</h2><p>Restrições que impedem a cobertura no recorte.</p></div></div>
                {dashboard.unassigned_reasons.length ? <div className="bar-chart constraint-bars">{dashboard.unassigned_reasons.map((item) => <div className="bar-row" key={item.reason}><div><span>{labelReason(item.reason)}</span><strong>{item.count}</strong></div><div className="bar-track"><span style={{ width: `${(100 * item.count) / maxReason}%` }} /></div></div>)}</div> : <div className="chart-empty state-success">Nenhuma oferta sem alocação neste recorte.</div>}
              </section>

              <section className="panel chart-panel">
                <div className="section-title"><div><span className="step-kicker">CAPACIDADE ALOCADA</span><h2>Horas cobertas por etapa</h2><p>Somente ofertas com docente definido.</p></div></div>
                <div className="stage-comparison"><div><span>1ª + estendida</span><strong>{dashboard.stage_hours.first_stage ?? 0}h</strong></div><div><span>2ª + estendida</span><strong>{dashboard.stage_hours.second_stage ?? 0}h</strong></div></div>
                <p className="chart-note">{dashboard.metric_notes.demand}</p>
              </section>
            </div>

            <footer className="source-note"><span>Fonte</span>{dashboard.source_note}<br />{dashboard.metric_notes.capacity_delta}<a className="inline-link" href="#/insights">Explorar oportunidades →</a></footer>
          </div>
        </div>
      )}
    </div>
  );
}
