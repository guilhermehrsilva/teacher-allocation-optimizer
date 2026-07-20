import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  addScenarioChange,
  addScenarioPolicy,
  createScenario,
  deleteScenarioChange,
  deleteScenarioPolicy,
  getJob,
  getScenario,
  getScenarioCatalog,
  getScenarioComparison,
  getSummary,
  listJobs,
  listScenarios,
  promoteScenario,
  resetPrimaryJobs,
  resetSavedScenarios,
  runScenario,
} from "../api";
import LoadingState from "../components/LoadingState";
import StatusBadge, { humanizeStatus, statusTone } from "../components/StatusBadge";
import { formatAnalysisJobLabel } from "../jobPresentation";
import type {
  Job,
  Scenario,
  ScenarioCatalog,
  ScenarioComparison,
  Summary,
} from "../types";

const executiveMoves = [
  { key: "CAPACIDADE", icon: "CH", title: "Reforçar ou reduzir capacidade", decision: "Contratar, afastar, retornar ou alterar CH letiva.", fields: ["STATUS", "CH_LETIVA"], impact: "Cobertura, déficit de CH e custo de capacidade" },
  { key: "AGENDA", icon: "AG", title: "Reorganizar agenda", decision: "Mover ofertas entre dia, horário ou metade do módulo.", fields: ["DIA_AULA", "HORÁRIO", "ORDEM"], impact: "Choques, cobertura e concentração diária" },
  { key: "COMPATIBILIDADE", icon: "PF", title: "Ampliar compatibilidade", decision: "Adicionar perfil docente ou revisar o perfil exigido pela oferta.", fields: ["PERFIL_DISCIPLINA"], impact: "Candidatos elegíveis e risco de candidato único" },
  { key: "ALOCAR_CLUSTER", icon: "CL", title: "Alocar docentes do cluster", decision: "Buscar docentes com CH disponível no cluster para recuperar disciplinas sem alocação.", fields: ["CLUSTER", "CH DISPONÍVEL", "AGENDA"], impact: "Cobertura das lacunas com flexibilização controlada de perfil" },
  { key: "PRIORIDADE", icon: "PR", title: "Proteger prioridades acadêmicas", decision: "Definir cursos e disciplinas que não podem perder cobertura.", fields: ["CURSO", "OFERTA"], impact: "Cobertura das ofertas estratégicas" },
  { key: "FIXAR", icon: "BL", title: "Fixar decisões", decision: "Preservar alocações homologadas e recalcular o restante.", fields: ["OFERTA", "DOCENTE", "CHAPA"], impact: "Estabilidade, trocas e esforço de implantação" },
] as const;

type MoveKey = typeof executiveMoves[number]["key"];
type EntityType = "teacher" | "offer";

const dayOptions = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO", "NSA"];
const statusOptions = ["ATIVO", "DEMITIDO", "LICENÇA MATER.", "LICENÇA MATER. COMPL. 180 DIAS"];

function signed(value: number, suffix = "") {
  return `${value > 0 ? "+" : ""}${value}${suffix}`;
}

function deltaInterpretation(value: number, positiveIsGood: boolean) {
  if (value === 0) return { className: "delta-neutral", label: "Sem alteração" };
  const improves = positiveIsGood ? value > 0 : value < 0;
  return improves
    ? { className: "delta-improvement", label: "Melhora" }
    : { className: "delta-regression", label: "Piora" };
}

function ScenarioMetricCard({
  title,
  value,
  delta,
  positiveIsGood,
  detail,
  featured = false,
}: {
  title: string;
  value: string;
  delta: number;
  positiveIsGood: boolean;
  detail: string;
  featured?: boolean;
}) {
  const interpretation = deltaInterpretation(delta, positiveIsGood);
  return <article className={`kpi-card scenario-delta-card ${interpretation.className} ${featured ? "featured" : ""}`}><span>{title}</span><strong>{value}</strong><small><b>{interpretation.label}</b>{detail}</small></article>;
}

export default function ScenariosPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [active, setActive] = useState<Scenario | null>(null);
  const [baseline, setBaseline] = useState("");
  const [baselineSummary, setBaselineSummary] = useState<Summary | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedMove, setSelectedMove] = useState<MoveKey>("CAPACIDADE");
  const [entityType, setEntityType] = useState<EntityType>("teacher");
  const [rowNumber, setRowNumber] = useState("");
  const [entitySearch, setEntitySearch] = useState("");
  const [fieldName, setFieldName] = useState("STATUS");
  const [newValue, setNewValue] = useState("");
  const [configuratorOpen, setConfiguratorOpen] = useState(false);
  const [policyTargetType, setPolicyTargetType] = useState("COURSE");
  const [policyTargetValue, setPolicyTargetValue] = useState("");
  const [catalog, setCatalog] = useState<ScenarioCatalog | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [resetTarget, setResetTarget] = useState<"baseline" | "scenario" | null>(null);
  const baselineRequest = useRef(0);
  const scenarioDetailRequest = useRef(0);
  const resetDialogRef = useRef<HTMLElement>(null);
  const resetCancelRef = useRef<HTMLButtonElement>(null);
  const busyRef = useRef(false);

  useEffect(() => { busyRef.current = busy; }, [busy]);

  useEffect(() => {
    if (!resetTarget) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    resetCancelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busyRef.current) {
        setResetTarget(null);
        return;
      }
      if (event.key !== "Tab" || !resetDialogRef.current) return;
      const focusable = Array.from(resetDialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled)"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [resetTarget]);

  const refreshScenarios = async (preferredId?: string) => {
    const items = await listScenarios();
    setScenarios(items);
    const selected = items.find((item) => item.id === (preferredId ?? active?.id));
    if (selected) setActive(selected);
  };

  useEffect(() => {
    let live = true;
    void Promise.all([listJobs(), listScenarios()]).then(([jobItems, scenarioItems]) => {
      if (!live) return;
      const complete = jobItems.filter((item) => item.status === "CONCLUIDA");
      setJobs(complete);
      setScenarios(scenarioItems);
      if (complete[0]) setBaseline(complete[0].id);
      if (scenarioItems[0]) setActive(scenarioItems[0]);
    }).catch((requestError: Error) => { if (live) setError(requestError.message); })
      .finally(() => { if (live) setInitialLoading(false); });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    const baselineId = active?.baseline_job_id ?? baseline;
    if (!baselineId) {
      setBaselineSummary(null);
      return;
    }
    const requestId = ++baselineRequest.current;
    let live = true;
    setBaselineSummary(null);
    void getSummary(baselineId)
      .then((payload) => { if (live && requestId === baselineRequest.current) setBaselineSummary(payload); })
      .catch(() => { if (live && requestId === baselineRequest.current) setBaselineSummary(null); });
    return () => { live = false; };
  }, [baseline, active?.baseline_job_id]);

  useEffect(() => {
    if (!active) {
      setCatalog(null);
      setComparison(null);
      setCatalogLoading(false);
      setComparisonLoading(false);
      return;
    }
    const requestId = ++scenarioDetailRequest.current;
    let live = true;
    setError("");
    setCatalog(null);
    setCatalogLoading(true);
    setComparison(null);
    setComparisonLoading(active.latest_job?.status === "CONCLUIDA");
    void getScenarioCatalog(active.id)
      .then((payload) => { if (live && requestId === scenarioDetailRequest.current) setCatalog(payload); })
      .catch((requestError: Error) => { if (live && requestId === scenarioDetailRequest.current) setError(requestError.message); })
      .finally(() => { if (live && requestId === scenarioDetailRequest.current) setCatalogLoading(false); });
    if (active.latest_job?.status === "CONCLUIDA") {
      void getScenarioComparison(active.id)
        .then((payload) => { if (live && requestId === scenarioDetailRequest.current) setComparison(payload); })
        .catch((requestError: Error) => { if (live && requestId === scenarioDetailRequest.current) { setComparison(null); setError(`Não foi possível carregar a comparação: ${requestError.message}`); } })
        .finally(() => { if (live && requestId === scenarioDetailRequest.current) setComparisonLoading(false); });
    }
    return () => { live = false; };
  }, [active?.id, active?.latest_job?.status]);

  useEffect(() => {
    const latest = active?.latest_job;
    if (!latest || latest.terminal) return;
    const timer = window.setInterval(async () => {
      try {
        const current = await getJob(latest.id);
        setActive((previous) => previous ? { ...previous, latest_job: current, status: current.terminal ? previous.status : "EXECUTANDO" } : previous);
        if (current.terminal) {
          window.clearInterval(timer);
          const refreshed = await getScenario(active.id);
          setActive(refreshed);
          await refreshScenarios(refreshed.id);
        }
      } catch (requestError) {
        setError((requestError as Error).message);
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [active?.id, active?.latest_job?.id, active?.latest_job?.terminal]);

  const move = executiveMoves.find((item) => item.key === selectedMove) ?? executiveMoves[0];
  const advancedMove = ["ALOCAR_CLUSTER", "PRIORIDADE", "FIXAR"].includes(selectedMove);
  const fields = useMemo(() => {
    if (selectedMove === "CAPACIDADE") return ["STATUS", "CH_LETIVA"];
    if (selectedMove === "AGENDA") return ["DIA_AULA", "HORÁRIO", "ORDEM"];
    if (selectedMove === "COMPATIBILIDADE") return ["PERFIL_DISCIPLINA"];
    return [];
  }, [selectedMove]);
  const entities = entityType === "teacher" ? catalog?.teachers ?? [] : catalog?.offers ?? [];
  const filteredEntities = useMemo(() => {
    if (!entitySearch.trim()) return entities;
    const needle = entitySearch.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
    return entities.filter((item) => {
      const searchable = ("discipline_name" in item
        ? [item.discipline_name, item.discipline_code, item.course, item.course_code, item.row_number]
        : [item.name, item.badge, item.job_function, item.status, item.profile, item.row_number])
        .join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
      return searchable.includes(needle);
    });
  }, [entities, entitySearch, entityType]);
  const baselineCoverage = baselineSummary?.transmissions
    ? (100 * baselineSummary.allocated) / baselineSummary.transmissions
    : 0;
  const premiseCount = (active?.changes.length ?? 0) + (active?.policies.length ?? 0);
  const readOnly = Boolean(active && (active.status === "HOMOLOGADO" || active.official_job_id));
  const promotionBlockers = useMemo(() => {
    if (!comparison || comparison.guardrails.eligible_for_promotion) return [];
    const blockers: string[] = [];
    if (statusTone(comparison.guardrails.validation) !== "success") blockers.push(`Validação: ${humanizeStatus(comparison.guardrails.validation)}.`);
    if (statusTone(comparison.guardrails.solver) !== "success") blockers.push(`Solver: ${humanizeStatus(comparison.guardrails.solver)}.`);
    if (statusTone(comparison.guardrails.audit) !== "success") blockers.push(`Auditoria: ${humanizeStatus(comparison.guardrails.audit)}.`);
    if (!blockers.length) blockers.push("O cenário não atende a todos os critérios internos de homologação.");
    return blockers;
  }, [comparison]);

  const resetEditor = (moveKey: MoveKey) => {
    setSelectedMove(moveKey);
    const nextEntity: EntityType = moveKey === "AGENDA" ? "offer" : "teacher";
    setEntityType(nextEntity);
    setRowNumber("");
    setEntitySearch("");
    setNewValue("");
    setPolicyTargetType(moveKey === "ALOCAR_CLUSTER" ? "CLUSTER" : moveKey === "FIXAR" ? "OFFER" : "COURSE");
    setPolicyTargetValue("");
    setFieldName(moveKey === "CAPACIDADE" ? "STATUS" : moveKey === "AGENDA" ? "DIA_AULA" : "PERFIL_DISCIPLINA");
  };

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!baseline || name.trim().length < 3) return;
    setBusy(true);
    setError("");
    try {
      const created = await createScenario(baseline, name, description);
      setActive(created);
      setName("");
      setDescription("");
      await refreshScenarios(created.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleAddChange = async (event: FormEvent) => {
    event.preventDefault();
    if (!active || readOnly || !rowNumber || newValue === "" || advancedMove) return;
    setBusy(true);
    setError("");
    try {
      await addScenarioChange(active.id, {
        change_type: selectedMove,
        entity_type: entityType,
        row_number: Number(rowNumber),
        field_name: fieldName,
        new_value: fieldName === "CH_LETIVA" ? Number(newValue) : newValue,
      });
      const refreshed = await getScenario(active.id);
      setActive(refreshed);
      await refreshScenarios(active.id);
      setNewValue("");
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleAddPolicy = async (event: FormEvent) => {
    event.preventDefault();
    if (!active || readOnly || !advancedMove) return;
    const targetValue = policyTargetValue;
    if (!targetValue) return;
    setBusy(true);
    setError("");
    try {
      const selectedOffer = catalog?.offers.find((item) => item.row_number === Number(targetValue));
      await addScenarioPolicy(active.id, {
        policy_type: selectedMove,
        target_type: policyTargetType,
        target_value: targetValue,
        configuration: selectedMove === "FIXAR" ? { teacher_badge: selectedOffer?.baseline_teacher_badge ?? "" } : {},
      });
      const refreshed = await getScenario(active.id);
      setActive(refreshed);
      await refreshScenarios(active.id);
      setPolicyTargetValue("");
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteChange = async (changeId: string) => {
    if (!active || readOnly) return;
    setBusy(true);
    setError("");
    try {
      await deleteScenarioChange(active.id, changeId);
      const refreshed = await getScenario(active.id);
      setActive(refreshed);
      await refreshScenarios(active.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!active || readOnly) return;
    setBusy(true);
    setError("");
    try {
      await deleteScenarioPolicy(active.id, policyId);
      const refreshed = await getScenario(active.id);
      setActive(refreshed);
      await refreshScenarios(active.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleRun = async () => {
    if (!active || readOnly) return;
    setBusy(true);
    setError("");
    setComparison(null);
    try {
      const job = await runScenario(active.id);
      setActive({ ...active, status: "EXECUTANDO", latest_job: job });
      await refreshScenarios(active.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handlePromote = async () => {
    if (!active || !comparison?.guardrails.eligible_for_promotion) return;
    if (!window.confirm("Homologar esta simulação como resultado final do módulo? O histórico anterior será preservado.")) return;
    setBusy(true);
    setError("");
    try {
      const promoted = await promoteScenario(active.id);
      setActive(promoted);
      await refreshScenarios(promoted.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async (scope: "latest" | "all") => {
    if (!resetTarget) return;
    setBusy(true);
    setError("");
    try {
      if (resetTarget === "baseline") await resetPrimaryJobs(scope);
      else await resetSavedScenarios(scope);
      const [jobItems, scenarioItems] = await Promise.all([listJobs(), listScenarios()]);
      const complete = jobItems.filter((item) => item.status === "CONCLUIDA");
      setJobs(complete);
      setScenarios(scenarioItems);
      setBaseline(complete[0]?.id ?? "");
      setActive(scenarioItems[0] ?? null);
      setConfiguratorOpen(Boolean(scenarioItems[0]));
      setCatalog(null);
      setComparison(null);
      setResetTarget(null);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const renderValueControl = () => {
    if (fieldName === "STATUS") return <select disabled={readOnly} value={newValue} onChange={(event) => setNewValue(event.target.value)}><option value="">Selecione</option>{statusOptions.map((item) => <option key={item}>{item}</option>)}</select>;
    if (fieldName === "DIA_AULA") return <select disabled={readOnly} value={newValue} onChange={(event) => setNewValue(event.target.value)}><option value="">Selecione</option>{dayOptions.map((item) => <option key={item}>{item}</option>)}</select>;
    if (fieldName === "ORDEM") return <select disabled={readOnly} value={newValue} onChange={(event) => setNewValue(event.target.value)}><option value="">Selecione</option>{["1ª", "2ª", "ESTENDIDA"].map((item) => <option key={item}>{item}</option>)}</select>;
    return <input disabled={readOnly} type={fieldName === "CH_LETIVA" ? "number" : "text"} min={fieldName === "CH_LETIVA" ? 0 : undefined} placeholder={fieldName === "HORÁRIO" ? "19:00" : "Novo valor"} value={newValue} onChange={(event) => setNewValue(event.target.value)} />;
  };

  return <div className="page-container">
    <div className="page-heading"><div><p className="eyebrow">Decisão executiva</p><h1>Cenários de reajuste</h1><p>Simule o futuro em um motor secundário, compare com a alocação oficial e homologue somente o resultado escolhido.</p></div><span className="phase-badge">Motor secundário isolado</span></div>
    {error && <div className="alert error" role="alert">{error}</div>}
    {initialLoading && <LoadingState title="Carregando o ambiente de cenários" description="Rodadas-base, cenários salvos e estados de auditoria estão sendo recuperados." />}

    {!initialLoading && <section className="panel scenario-intro">
      <div><span className="step-kicker">BASELINE IMUTÁVEL</span><h2>Escolha a rodada oficial de comparação</h2><p>Cada cenário terá sua própria fonte, solução, auditoria e diferenças em relação a esta rodada.</p></div>
      <div className="scenario-intro-controls">
        <div className="scenario-select-action"><label className="field"><span>Rodada-base</span><select value={active?.baseline_job_id ?? baseline} disabled={Boolean(active)} onChange={(event) => setBaseline(event.target.value)}>{jobs.length === 0 && <option value="">Execute uma rodada primeiro</option>}{jobs.map((job) => <option value={job.id} key={job.id}>{formatAnalysisJobLabel(job)}</option>)}</select></label><button type="button" className="scenario-reset-trigger" disabled={!jobs.length || busy} onClick={() => setResetTarget("baseline")}>Zerar rodadas-base</button></div>
        <div className="scenario-select-action"><label className="field"><span>Cenário salvo</span><select value={active?.id ?? ""} onChange={(event) => { const selected = scenarios.find((item) => item.id === event.target.value) ?? null; setActive(selected); setConfiguratorOpen(Boolean(selected)); }}><option value="">Novo cenário</option>{scenarios.map((item) => <option value={item.id} key={item.id}>{item.name} · Módulo {item.module} · {humanizeStatus(item.status)}</option>)}</select></label><button type="button" className="scenario-reset-trigger" disabled={!scenarios.length || busy} onClick={() => setResetTarget("scenario")}>Zerar cenários salvos</button></div>
      </div>
    </section>}

    {resetTarget && <section ref={resetDialogRef} className="scenario-reset-confirmation" role="dialog" aria-modal="true" aria-labelledby="reset-title" aria-describedby="reset-description"><div><span className="step-kicker">CONFIRMAÇÃO</span><h2 id="reset-title">{resetTarget === "baseline" ? "Zerar rodadas-base" : "Zerar cenários salvos"}</h2><p id="reset-description">{resetTarget === "baseline" ? "Ao remover uma rodada-base, seus cenários vinculados também serão excluídos." : "As rodadas-base serão preservadas; somente os cenários e suas simulações serão excluídos."} Esta ação não pode ser desfeita.</p></div><div className="scenario-reset-actions"><button ref={resetCancelRef} type="button" className="button secondary" disabled={busy} onClick={() => setResetTarget(null)}>Cancelar</button><button type="button" className="button secondary danger" disabled={busy} onClick={() => void handleReset("latest")}>Somente o último</button><button type="button" className="button primary danger" disabled={busy} onClick={() => void handleReset("all")}>Zerar todos</button></div></section>}

    <section className="scenario-workflow" aria-label="Fluxo de cenários"><div className="active"><span>01</span><strong>Escolher movimento</strong></div><div className={configuratorOpen ? "active" : ""}><span>02</span><strong>Editar premissas</strong></div><div className={active?.latest_job ? "active" : ""}><span>03</span><strong>Reprocessar e auditar</strong></div><div className={comparison ? "active" : ""}><span>04</span><strong>Comparar e decidir</strong></div></section>

    <div className="executive-moves">{executiveMoves.map((item) => <button type="button" className={selectedMove === item.key ? "active" : ""} aria-pressed={selectedMove === item.key} onClick={() => resetEditor(item.key)} key={item.title}><span>{item.icon}</span><div><strong>{item.title}</strong><small>{item.decision}</small></div></button>)}</div>

    <section className="panel scenario-builder-preview"><div><span className="step-kicker">MOVIMENTO SELECIONADO</span><h2>{move.title}</h2><p>{move.decision}</p><div className="field-chips">{move.fields.map((field) => <span key={field}>{field}</span>)}</div></div><div className="impact-preview"><span>Impacto esperado</span><strong>{move.impact}</strong><small>A simulação nunca substituirá automaticamente a rodada oficial.</small></div><button className="button primary" disabled={(!baseline && !active) || readOnly} onClick={() => setConfiguratorOpen(true)}>{readOnly ? "Cenário somente leitura" : "Configurar cenário"}</button></section>

    {configuratorOpen && !active && <form className="panel scenario-create" onSubmit={handleCreate}>
      <div className="section-title"><div><span className="step-kicker">NOVO CENÁRIO</span><h2>Defina a pergunta da simulação</h2></div></div>
      <div className="scenario-create-grid">
        <label className="field"><span>Nome do cenário</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Retorno de docentes licenciados" /></label>
        <label className="field scenario-description"><span>Objetivo e justificativa</span><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Qual hipótese ou decisão será testada?" /></label>
        <button className="button primary" disabled={!baseline || name.trim().length < 3 || busy}>Criar e configurar</button>
      </div>
    </form>}

    {active && <>
      <section className="scenario-baseline-strip" aria-label="Resumo da baseline">
        <div><span>Baseline</span><strong>{active.baseline_round}</strong><small>Módulo {active.module}</small></div>
        <div><span>Cobertura original</span><strong>{baselineSummary ? `${baselineCoverage.toFixed(2)}%` : "—"}</strong><small>{baselineSummary ? `${baselineSummary.allocated}/${baselineSummary.transmissions} ofertas` : "Carregando baseline"}</small></div>
        <div><span>Pendências</span><strong>{baselineSummary?.unassigned ?? "—"}</strong><small>antes da simulação</small></div>
        <div><span>Premissas</span><strong>{premiseCount}</strong><small>alterações e políticas</small></div>
        <div><span>Status</span><StatusBadge value={active.status} /><small>{active.official_job_id ? "resultado oficial" : "ambiente isolado"}</small></div>
      </section>

      {readOnly && <section className="scenario-readonly-notice" role="status"><div><span className="step-kicker">CENÁRIO HOMOLOGADO</span><strong>Este cenário está em modo somente leitura</strong><p>Premissas, políticas e o resultado oficial permanecem preservados. Crie um novo cenário para testar outra hipótese.</p></div><button type="button" className="button secondary" onClick={() => { setBaseline(active.baseline_job_id); setActive(null); setConfiguratorOpen(true); setName(`${active.name} · nova hipótese`); setDescription(active.description); }}>Criar novo cenário</button></section>}

      {configuratorOpen && <section className="panel scenario-builder-live">
        <div className="section-title"><div><span className="step-kicker">CONFIGURAÇÃO DO MOVIMENTO</span><h2>{move.title}</h2><p>{move.decision}</p></div><span className="scenario-capability ready">Funcional no motor secundário</span></div>
        {catalogLoading && <div className="inline-loading" role="status"><span className="mini-spinner" aria-hidden="true" />Carregando catálogo da rodada-base…</div>}
        {!catalogLoading && (advancedMove ? <ScenarioPolicyEditor move={selectedMove} catalog={catalog} targetType={policyTargetType} targetValue={policyTargetValue} busy={busy} readOnly={readOnly} onTargetType={(value) => { setPolicyTargetType(value); setPolicyTargetValue(""); }} onTargetValue={setPolicyTargetValue} onSubmit={handleAddPolicy} /> : <form className="scenario-change-form" onSubmit={handleAddChange}>
          {selectedMove === "COMPATIBILIDADE" && <label className="field"><span>Aplicar em</span><select disabled={readOnly} value={entityType} onChange={(event) => { setEntityType(event.target.value as EntityType); setRowNumber(""); setEntitySearch(""); }}><option value="teacher">Docente</option><option value="offer">Oferta</option></select></label>}
          <label className="field scenario-entity-field"><span>{entityType === "teacher" ? "Docente" : "Oferta"}</span><input disabled={readOnly} className="scenario-entity-search" type="search" value={entitySearch} onChange={(event) => { setEntitySearch(event.target.value); setRowNumber(""); }} placeholder={entityType === "teacher" ? "Digite nome, chapa, função, status ou perfil" : "Digite disciplina, código, curso ou linha"} aria-label={entityType === "teacher" ? "Buscar docente" : "Buscar oferta"} /><select disabled={readOnly} value={rowNumber} onChange={(event) => setRowNumber(event.target.value)}><option value="">{entitySearch ? `${filteredEntities.length} ${entityType === "teacher" ? "docente(s)" : "oferta(s)"} encontrado(s)` : "Selecione"}</option>{filteredEntities.map((item) => <option value={item.row_number} key={item.row_number}>{"name" in item ? `${item.name} · ${item.badge} · ${item.job_function}` : `${item.discipline_name} · ${item.discipline_code} · ${item.course} · linha ${item.row_number}`}</option>)}</select></label>
          <label className="field"><span>Campo</span><select disabled={readOnly} value={fieldName} onChange={(event) => { setFieldName(event.target.value); setNewValue(""); }}>{fields.map((field) => <option key={field}>{field}</option>)}</select></label>
          <label className="field"><span>Novo valor</span>{renderValueControl()}</label>
          <button className="button primary" disabled={readOnly || !rowNumber || newValue === "" || busy}>Adicionar alteração</button>
        </form>)}
      </section>}

      <section className="panel scenario-change-set">
        <div className="section-title"><div><span className="step-kicker">CONJUNTO DE PREMISSAS</span><h2>Premissas antes da simulação</h2><p>Alterações de dados e políticas do solver são registradas separadamente e aplicadas apenas ao cenário.</p></div><button className="button primary" disabled={readOnly || !premiseCount || busy || Boolean(active.latest_job && !active.latest_job.terminal)} onClick={() => void handleRun()}>{active.latest_job && !active.latest_job.terminal ? "Simulando…" : "Executar simulação"}</button></div>
        {premiseCount ? <div className="table-wrap"><table><thead><tr><th>Movimento</th><th>Alvo</th><th>Regra</th><th>Configuração</th><th /></tr></thead><tbody>
          {active.changes.map((change) => <tr key={change.id}><td>{change.change_type}</td><td>{change.entity_type === "teacher" ? "Docente" : "Oferta"} · linha {change.row_number}</td><td><strong>{change.field_name}</strong></td><td>{String(change.old_value ?? "Vazio")} → <strong>{String(change.new_value)}</strong></td><td><button className="text-action danger" disabled={busy || readOnly} onClick={() => void handleDeleteChange(change.id)}>Remover</button></td></tr>)}
          {active.policies.map((policy) => <tr key={policy.id}><td>{policy.policy_type}</td><td>{policy.target_type} · {policy.target_value}</td><td><strong>Política do motor secundário</strong></td><td>{policy.policy_type === "FIXAR" ? `Chapa ${String(policy.configuration.teacher_badge)}` : "Restrição ativa"}</td><td><button className="text-action danger" disabled={busy || readOnly} onClick={() => void handleDeletePolicy(policy.id)}>Remover</button></td></tr>)}
        </tbody></table></div> : <div className="chart-empty">Configure um dos seis movimentos para liberar a simulação.</div>}
        {active.latest_job && <div className="scenario-run-state"><span className={active.latest_job.terminal ? `status-${statusTone(active.latest_job.status)}` : "pulse"} /><div><StatusBadge value={active.latest_job.status} /><small>{active.latest_job.message}</small></div></div>}
      </section>

      {comparisonLoading && <LoadingState title="Comparando baseline e cenário" description="Deltas, trocas de docente e guardrails estão sendo consolidados." />}
      {comparison && <section className="scenario-comparison-section">
        <div className="section-title"><div><span className="step-kicker">BASELINE × CENÁRIO</span><h2>Impacto da simulação</h2><p>Os deltas abaixo foram recalculados sobre a solução auditada do motor secundário.</p></div></div>
        <div className="kpi-grid scenario-kpis">
          <ScenarioMetricCard featured title="Cobertura simulada" value={`${comparison.kpis.scenario_coverage_pct.toFixed(2)}%`} delta={comparison.kpis.coverage_delta_pp} positiveIsGood detail={`${signed(comparison.kpis.coverage_delta_pp, " pp")} vs. baseline`} />
          <ScenarioMetricCard title="Ofertas alocadas" value={signed(comparison.kpis.allocated_delta)} delta={comparison.kpis.allocated_delta} positiveIsGood detail={`${comparison.differences.recovered.length} recuperadas · ${comparison.differences.lost.length} perdidas`} />
          <ScenarioMetricCard title="Demanda pendente" value={signed(comparison.kpis.unassigned_hours_delta, "h")} delta={comparison.kpis.unassigned_hours_delta} positiveIsGood={false} detail="delta de horas não cobertas" />
          <article className="kpi-card"><span>Estabilidade</span><strong>{comparison.kpis.assignment_stability_pct.toFixed(1)}%</strong><small>{comparison.differences.reassigned.length} trocas de docente</small></article>
          <ScenarioMetricCard title="1ª etapa" value={signed(comparison.kpis.first_stage_hours_delta, "h")} delta={comparison.kpis.first_stage_hours_delta} positiveIsGood detail="delta de horas alocadas" />
          <ScenarioMetricCard title="2ª etapa" value={signed(comparison.kpis.second_stage_hours_delta, "h")} delta={comparison.kpis.second_stage_hours_delta} positiveIsGood detail="delta de horas alocadas" />
          <ScenarioMetricCard title="Horas internas" value={signed(comparison.kpis.internal_allocated_hours_delta, "h")} delta={comparison.kpis.internal_allocated_hours_delta} positiveIsGood detail="delta de alocações em contratos CLT" />
          <ScenarioMetricCard title="Exposição externa" value={signed(comparison.kpis.external_allocated_hours_delta, "h")} delta={comparison.kpis.external_allocated_hours_delta} positiveIsGood={false} detail="delta de horas fora do quadro interno" />
        </div>
        <div className="scenario-guardrail-results" aria-label="Guardrails para homologação"><span>Validação <StatusBadge value={comparison.guardrails.validation} /></span><span>Solver <StatusBadge value={comparison.guardrails.solver} /></span><span>Auditoria <StatusBadge value={comparison.guardrails.audit} /></span></div>
        <div className="scenario-difference-grid">
          <DifferenceList title="Ofertas recuperadas" items={comparison.differences.recovered} empty="Nenhuma oferta recuperada." />
          <DifferenceList title="Ofertas perdidas" items={comparison.differences.lost} empty="Nenhuma oferta perdeu cobertura." />
          <DifferenceList title="Docentes alterados" items={comparison.differences.reassigned} empty="Nenhuma troca de docente." />
        </div>
        <div className="scenario-promotion"><div><span className="step-kicker">HOMOLOGAÇÃO HUMANA</span><h2>Aplicar como resultado final</h2><p>A baseline e o resultado oficial anterior permanecerão arquivados e reversíveis.</p>{promotionBlockers.length > 0 && <div className="promotion-blockers" role="alert"><strong>Homologação bloqueada</strong><ul>{promotionBlockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul></div>}</div><button className="button primary" disabled={!comparison.guardrails.eligible_for_promotion || busy || readOnly} onClick={() => void handlePromote()}>{readOnly ? "Cenário homologado" : "Homologar e aplicar"}</button></div>
      </section>}
    </>}
  </div>;
}

function ScenarioPolicyEditor({
  move, catalog, targetType, targetValue, busy, readOnly, onTargetType, onTargetValue, onSubmit,
}: {
  move: MoveKey;
  catalog: ScenarioCatalog | null;
  targetType: string;
  targetValue: string;
  busy: boolean;
  readOnly: boolean;
  onTargetType: (value: string) => void;
  onTargetValue: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const [fixedSearch, setFixedSearch] = useState("");
  const fixedOffers = catalog?.offers.filter(
    (item) => item.baseline_status === "ALOCADA" && item.baseline_teacher_badge,
  ) ?? [];
  const normalizedFixedSearch = fixedSearch.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const filteredFixedOffers = fixedOffers.filter((item) => {
    if (!normalizedFixedSearch) return true;
    return [item.baseline_teacher_name, item.baseline_teacher_badge, item.discipline_name, item.discipline_code, item.course]
      .join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR")
      .includes(normalizedFixedSearch);
  });
  return <form className="scenario-policy-form" onSubmit={onSubmit}>
    {move === "ALOCAR_CLUSTER" && <><div className="scenario-policy-explanation"><strong>Flexibilização de perfil dentro do cluster</strong><p>O docente é considerado do cluster quando algum perfil dele aparece nas ofertas desse cluster. O motor pode então recuperar lacunas sem exigir o perfil exato, preservando CH por etapa, agenda, status e limite Stricto.</p></div><label className="field scenario-entity-field"><span>Cluster com lacunas</span><select disabled={readOnly} value={targetValue} onChange={(event) => onTargetValue(event.target.value)}><option value="">Selecione</option>{catalog?.clusters.map((item) => <option key={item.name} value={item.name}>{item.name} · {item.unassigned_offers} oferta(s) sem alocação</option>)}</select></label></>}
    {move === "PRIORIDADE" && <>
      <label className="field"><span>Proteger</span><select disabled={readOnly} value={targetType} onChange={(event) => onTargetType(event.target.value)}><option value="COURSE">Curso completo</option><option value="OFFER">Oferta específica</option></select></label>
      <label className="field scenario-entity-field"><span>{targetType === "COURSE" ? "Curso estratégico" : "Oferta estratégica"}</span><select disabled={readOnly} value={targetValue} onChange={(event) => onTargetValue(event.target.value)}><option value="">Selecione</option>{targetType === "COURSE" ? catalog?.courses.map((item) => <option key={item.code} value={item.code}>{item.name} · {item.code}</option>) : catalog?.offers.map((item) => <option key={item.row_number} value={item.row_number}>{item.discipline_name} · {item.course} · linha {item.row_number}</option>)}</select></label>
    </>}
    {move === "FIXAR" && <label className="field scenario-entity-field"><span>Alocação da baseline a preservar</span><input disabled={readOnly} className="scenario-entity-search" type="search" value={fixedSearch} onChange={(event) => { setFixedSearch(event.target.value); onTargetValue(""); }} placeholder="Digite professor, chapa, disciplina, código ou curso" aria-label="Buscar professor ou alocação fixada" /><select disabled={readOnly} value={targetValue} onChange={(event) => onTargetValue(event.target.value)}><option value="">{fixedSearch ? `${filteredFixedOffers.length} alocação(ões) encontrada(s)` : "Selecione"}</option>{filteredFixedOffers.map((item) => <option key={item.row_number} value={item.row_number}>{item.discipline_name} · {item.baseline_teacher_name} ({item.baseline_teacher_badge})</option>)}</select></label>}
    <button className="button primary" disabled={readOnly || busy || !targetValue}>Adicionar política</button>
  </form>;
}

function DifferenceList({ title, items, empty }: { title: string; items: ScenarioComparison["differences"]["recovered"]; empty: string }) {
  return <article className="panel scenario-difference-card"><h3>{title}<span>{items.length}</span></h3>{items.length ? <ul tabIndex={0} aria-label={`${title}: ${items.length} registros`}>{items.map((item) => <li key={item.source_row}><strong>{item.discipline_name}</strong><span>{item.discipline_code} · linha {item.source_row}</span>{(item.before_teacher || item.after_teacher) && <small>{item.before_teacher || "Sem docente"} → {item.after_teacher || "Sem docente"}</small>}</li>)}</ul> : <p>{empty}</p>}</article>;
}
