import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  artifactUrl,
  createJob,
  getAllocations,
  getJob,
  getSummary,
  listJobs,
  validateUpload,
} from "../api";
import ResetPrimaryRounds from "../components/ResetPrimaryRounds";
import type { AllocationPage, Job, Summary, UploadResult } from "../types";

const steps = ["Preparando", "Validando", "Otimizando", "Auditando", "Publicando"];

function stepIndex(status: string): number {
  if (status === "CONCLUIDA") return steps.length;
  if (["GRAVANDO_ALOCACAO"].includes(status)) return 4;
  if (["AUDITANDO"].includes(status)) return 3;
  if (["RESOLVENDO"].includes(status)) return 2;
  if (["VALIDANDO"].includes(status)) return 1;
  return 0;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default function ProcessPage() {
  const [file, setFile] = useState<File | null>(null);
  const [module, setModule] = useState<number | "">("");
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [confirmWarnings, setConfirmWarnings] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [allocations, setAllocations] = useState<AllocationPage | null>(null);
  const [allocationStatus, setAllocationStatus] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refreshJobs = async () => {
    try {
      setJobs(await listJobs());
    } catch {
      // O histórico é apoio; o fluxo principal continua disponível.
    }
  };

  useEffect(() => {
    void refreshJobs();
  }, []);

  useEffect(() => {
    if (!job || job.terminal) return;
    const timer = window.setInterval(async () => {
      try {
        const current = await getJob(job.id);
        setJob(current);
        if (current.terminal) void refreshJobs();
      } catch (requestError) {
        setError((requestError as Error).message);
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.terminal]);

  useEffect(() => {
    if (!job || job.status !== "CONCLUIDA") return;
    void getSummary(job.id).then(setSummary).catch((requestError: Error) => setError(requestError.message));
  }, [job?.id, job?.status]);

  useEffect(() => {
    if (!job || job.status !== "CONCLUIDA") return;
    void getAllocations(job.id, page, allocationStatus, search)
      .then(setAllocations)
      .catch((requestError: Error) => setError(requestError.message));
  }, [job?.id, job?.status, page, allocationStatus, search]);

  const validation = upload?.validation;
  const canRun =
    upload &&
    validation?.status !== "REPROVADO" &&
    (validation?.status !== "APROVADO_COM_RESSALVAS" || confirmWarnings);

  const currentStep = useMemo(() => stepIndex(job?.status ?? "QUEUED"), [job?.status]);

  const chooseFile = (selected: File | null) => {
    setFile(selected);
    setUpload(null);
    setConfirmWarnings(false);
    setError("");
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    chooseFile(event.target.files?.[0] ?? null);
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    chooseFile(event.dataTransfer.files?.[0] ?? null);
  };

  const handleValidate = async () => {
    if (!file || module === "") return;
    setBusy(true);
    setError("");
    setJob(null);
    setSummary(null);
    setAllocations(null);
    try {
      setUpload(await validateUpload(file, module));
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleRun = async () => {
    if (!upload) return;
    setBusy(true);
    setError("");
    try {
      const created = await createJob(upload.id, confirmWarnings);
      setJob(created);
      await refreshJobs();
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const openExistingJob = async (jobId: string) => {
    if (!jobId) return;
    setError("");
    setUpload(null);
    setSummary(null);
    setAllocations(null);
    try {
      setJob(await getJob(jobId));
    } catch (requestError) {
      setError((requestError as Error).message);
    }
  };

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchDraft);
  };

  const coverage = summary ? (100 * summary.allocated) / summary.transmissions : 0;

  return (
    <div className="page-container">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Execução auditável</p>
          <h1>Processar uma nova alocação</h1>
          <p>Valide a base, acompanhe cada etapa e consulte o resultado sem perder o histórico.</p>
        </div>
        <div className="page-heading-actions">
          {jobs.length > 0 && (
            <label className="compact-field">
              <span>Execuções recentes</span>
              <select value={job?.id ?? ""} onChange={(event) => void openExistingJob(event.target.value)}>
                <option value="">Selecionar execução</option>
                {jobs.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.round ?? "Na fila"} · {item.filename} · {statusLabel(item.status)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <ResetPrimaryRounds disabled={!jobs.length || jobs.some((item) => !item.terminal)} />
        </div>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}

      <section className="panel upload-panel">
        <div className="section-title">
          <div><span className="step-kicker">PASSO 1</span><h2>Arquivo de entrada</h2></div>
          <span className="muted">Somente .xlsx · até 50 MB</span>
        </div>
        <div className="upload-grid">
          <label
            className={`dropzone ${file ? "has-file" : ""}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
          >
            <input type="file" accept=".xlsx" onChange={onFileChange} />
            <span className="upload-icon" aria-hidden="true">↑</span>
            <strong>{file ? file.name : "Arraste a planilha ou clique para selecionar"}</strong>
            <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "A fonte será copiada e preservada na rodada"}</span>
          </label>
          <div className="upload-actions">
            <label className="field">
              <span>Módulo esperado</span>
              <select value={module} onChange={(event) => setModule(event.target.value ? Number(event.target.value) : "")}>
                <option value="" disabled>Selecione o Módulo</option>
                {[51, 52, 53, 54].map((value) => <option value={value} key={value}>Módulo {value}</option>)}
              </select>
            </label>
            <button className="button primary" disabled={!file || module === "" || busy} onClick={() => void handleValidate()}>
              {busy && !upload ? "Validando…" : "Validar arquivo"}
            </button>
            <p>A otimização só será liberada após a validação dos dados.</p>
          </div>
        </div>
      </section>

      {busy && !upload && (
        <section className="panel loading-stage-panel" aria-live="polite">
          <div className="loading-orbit" aria-hidden="true"><span /><span /><span /></div>
          <div><span className="step-kicker">VALIDAÇÃO EM CURSO</span><h2>Conferindo estrutura e regras da base</h2><p>O arquivo está sendo preservado, lido e validado antes de liberar a otimização.</p></div>
          <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
        </section>
      )}

      {validation && (
        <section className="panel">
          <div className="section-title">
            <div><span className="step-kicker">PASSO 2</span><h2>Resultado da validação</h2></div>
            <span className={`status-badge ${validation.status.toLowerCase()}`}>{statusLabel(validation.status)}</span>
          </div>
          <div className="validation-summary">
            <div><strong>{validation.metadata.allocating_rows}</strong><span>ofertas alocáveis</span></div>
            <div><strong>{validation.summary.issue_groups}</strong><span>grupos de ocorrência</span></div>
            <div><strong>{validation.summary.blocking_issue_groups}</strong><span>grupos bloqueantes</span></div>
          </div>
          {validation.issues.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Severidade</th><th>Local</th><th>Ocorrência</th><th>Linhas</th></tr></thead>
                <tbody>
                  {validation.issues.map((issue) => (
                    <tr key={`${issue.code}-${issue.sheet}-${issue.column}`}>
                      <td><span className={`severity ${issue.severity.toLowerCase()}`}>{issue.severity}</span></td>
                      <td>{issue.sheet}<small>{issue.column}</small></td>
                      <td>{issue.message}</td>
                      <td>{issue.rows.slice(0, 6).join(", ")}{issue.rows.length > 6 ? "…" : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="validation-actions">
            <a className="button secondary" href={`/api/uploads/${upload.id}/validation.xlsx`}>Baixar planilha de pendências</a>
            {validation.status === "APROVADO_COM_RESSALVAS" && (
              <label className="confirmation">
                <input type="checkbox" checked={confirmWarnings} onChange={(event) => setConfirmWarnings(event.target.checked)} />
                Li as ressalvas e desejo executar a alocação.
              </label>
            )}
            <button className="button primary" disabled={!canRun || busy} onClick={() => void handleRun()}>
              Executar alocação
            </button>
          </div>
        </section>
      )}

      {job && (
        <section className="panel" aria-live="polite">
          <div className="section-title">
            <div><span className="step-kicker">PASSO 3</span><h2>Acompanhamento</h2></div>
            <span className={`status-badge ${job.status === "CONCLUIDA" ? "aprovado" : "running"}`}>
              {statusLabel(job.status)}
            </span>
          </div>
          <div className="job-meta">
            <span>{job.round ?? "Aguardando rodada"}</span>
            <span>{job.filename}</span>
            <span>Início {formatDate(job.created_at)}</span>
          </div>
          <ol className="stepper">
            {steps.map((step, index) => (
              <li className={index < currentStep ? "done" : index === currentStep ? "current" : ""} key={step}>
                <span>{index < currentStep ? "✓" : index + 1}</span>
                <strong>{step}</strong>
              </li>
            ))}
          </ol>
          <div className="process-message stage-transition" key={job.status}>
            <span className={!job.terminal ? "pulse" : ""} aria-hidden="true" />
            <div><strong>{job.message}</strong><small>Tempo decorrido e eventos reais — sem percentual estimado.</small></div>
            {!job.terminal && <div className="stage-spinner" aria-hidden="true" />}
          </div>
        </section>
      )}

      {summary && job && (
        <section className="panel result-section">
          <div className="section-title">
            <div><span className="step-kicker">RESULTADO</span><h2>Rodada concluída e auditada</h2></div>
            <span className="status-badge aprovado">CP-SAT {summary.solver_status}</span>
          </div>
          <div className="kpi-grid">
            <article className="kpi-card featured"><span>Cobertura</span><strong>{coverage.toFixed(2)}%</strong><small>{summary.allocated} de {summary.transmissions} ofertas</small></article>
            <article className="kpi-card"><span>Não alocadas</span><strong>{summary.unassigned}</strong><small>Exigem análise dos motivos</small></article>
            <article className="kpi-card"><span>Docentes utilizados</span><strong>{summary.used_teachers}</strong><small>de {summary.active_teachers} ativos</small></article>
            <article className="kpi-card"><span>Tempo do motor</span><strong>{summary.wall_time_seconds.toFixed(1)}s</strong><small>Solução {summary.solver_status.toLowerCase()}</small></article>
          </div>

          <div className="downloads">
            <strong>Artefatos da rodada</strong>
            <a href={artifactUrl(job.id, "allocation_workbook")}>Resultado Excel</a>
            <a href={artifactUrl(job.id, "allocation_summary")}>Resumo JSON</a>
            <a href={artifactUrl(job.id, "audit_report")}>Auditoria</a>
            <a href={artifactUrl(job.id, "validation_issues")}>Inconsistências</a>
            <a href={artifactUrl(job.id, "manifest")}>Manifesto</a>
            <a href={artifactUrl(job.id, "status")}>Histórico</a>
            <a className="analysis-link" href="#/insights">Analisar insights →</a>
          </div>

          <div className="table-toolbar">
            <div>
              <h3>Decisões de alocação</h3>
              <span>{allocations?.total ?? 0} registros encontrados</span>
            </div>
            <form onSubmit={submitSearch}>
              <select value={allocationStatus} onChange={(event) => { setPage(1); setAllocationStatus(event.target.value); }}>
                <option value="">Todos os status</option>
                <option value="ALOCADA">Alocadas</option>
                <option value="NAO_ALOCADA">Não alocadas</option>
              </select>
              <input placeholder="Disciplina, docente ou chapa" value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} />
              <button className="button secondary" type="submit">Buscar</button>
            </form>
          </div>
          {allocations && (
            <>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Status</th><th>Disciplina</th><th>Docente</th><th>Candidatos</th><th>Justificativa</th></tr></thead>
                  <tbody>
                    {allocations.items.map((item) => (
                      <tr key={item.transmission_id}>
                        <td><span className={`allocation-status ${item.status.toLowerCase()}`}>{statusLabel(item.status)}</span></td>
                        <td><strong>{item.discipline_name}</strong><small>{item.discipline_code} · {item.curriculum}</small></td>
                        <td>{item.teacher_name ?? "—"}<small>{item.teacher_badge ?? item.contract_model}</small></td>
                        <td>{item.eligible_teacher_count}</td>
                        <td>{item.unassigned_reason || item.allocation_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
                <span>Página {allocations.page} de {allocations.pages}</span>
                <button disabled={page >= allocations.pages} onClick={() => setPage(page + 1)}>Próxima</button>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
