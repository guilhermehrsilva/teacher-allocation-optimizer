import { useEffect, useState } from "react";
import { getDashboard, listAnalysisJobs } from "../api";
import LoadingState from "../components/LoadingState";
import StatusBadge from "../components/StatusBadge";
import { formatAnalysisJobLabel, jobContextLabel } from "../jobPresentation";
import type { DashboardData, Job } from "../types";

export default function ExportPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listAnalysisJobs()
      .then((items) => {
        if (!active) return;
        const complete = items.filter((item) => item.status === "CONCLUIDA");
        setJobs(complete);
        if (complete[0]) setSelected(complete[0].id);
      })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selected) {
      setDashboard(null);
      return;
    }
    let active = true;
    void getDashboard(selected, { order: [], day: [], time: [], cluster: [], course: [] })
      .then((payload) => { if (active) setDashboard(payload); })
      .catch(() => { if (active) setDashboard(null); });
    return () => { active = false; };
  }, [selected]);

  const selectedJob = jobs.find((item) => item.id === selected) ?? null;

  const getArtifactUrl = (artifactKey: string) => {
    if (!selectedJob) return "#";
    return `/api/jobs/${selectedJob.id}/artifacts/${artifactKey}`;
  };

  return (
    <div className="page-stack">
      <header className="page-header export-page-header">
        <div>
          <span className="step-kicker">FASE 05 · SAÍDA OFICIAL</span>
          <h1>Exportação e Relatórios de Alocação</h1>
          <p>
            Baixe a planilha final de alocação no formato <strong>.XLSX</strong> pronta para publicação acadêmica e uso operacional, além de relatórios de auditoria criptográfica e métricas executivas.
          </p>
        </div>
        {jobs.length > 0 && (
          <label className="context-select-label">
            <span>Rodada ou cenário a exportar</span>
            <select
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
              aria-label="Selecionar rodada ou cenário para exportação"
            >
              {jobs.map((item) => (
                <option key={item.id} value={item.id}>
                  {formatAnalysisJobLabel(item)}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      {loading && <LoadingState title="Carregando pacotes de exportação..." description="Localizando planilhas consolidadas e manifestos de auditoria do algoritmo OPTIMAL." />}
      {error && <div className="state-empty error"><p>{error}</p></div>}

      {!loading && !error && jobs.length === 0 && (
        <div className="state-empty">
          <h3>Nenhuma alocação concluída para exportar</h3>
          <p>Realize o processamento de uma base na aba <strong>Processamento</strong> ou execute um cenário para liberar o download das planilhas oficiais.</p>
          <a className="button" href="#/processamento">Ir para Processamento</a>
        </div>
      )}

      {!loading && !error && selectedJob && (
        <>
          {/* BARRA DE STATUS DO CONTEXTO ATUAL */}
          <div className="export-context-banner">
            <div className="export-context-info">
              <span className="context-label">Arquivo de origem para download:</span>
              <strong>{jobContextLabel(selectedJob)}</strong>
              <StatusBadge value={selectedJob.status} />
            </div>
            <div className="export-context-timestamp">
              <span>Geração: {new Date(selectedJob.updated_at || selectedJob.created_at).toLocaleString("pt-BR")}</span>
            </div>
          </div>

          {/* HERO CARD DE EXPORTAÇÃO DA PLANILHA OFICIAL (.XLSX) */}
          <section className="hero-export-card">
            <div className="hero-export-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="48" height="48" rx="12" fill="#0078D4" fillOpacity="0.15" />
                <path d="M28 14H16C14.8954 14 14 14.8954 14 16V32C14 33.1046 14.8954 34 16 34H32C33.1046 34 34 33.1046 34 32V20L28 14Z" stroke="#00D2FF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M28 14V20H34" stroke="#00D2FF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M19 23L25 29M25 23L19 29" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="hero-export-content">
              <span className="hero-export-tag">PLANILHA FINAL COMPLETA · ARQUIVO OFICIAL</span>
              <h2>Planilha de Alocação Docente (.XLSX)</h2>
              <p>
                O arquivo Excel consolidado contendo a grade geral alocada com precisão pelo algoritmo <strong>OPTIMAL</strong>. Inclui todas as associações entre docentes, disciplinas, turmas, dias da semana e horários, além de relatórios das lacunas remanescentes e carga letiva individual.
              </p>
              <ul className="hero-export-features">
                <li>✓ Grade completa formatada e pronta para impressão ou importação no ERP</li>
                <li>✓ Visão detalhada por docente com cálculo de CH letiva e saldo de horas</li>
                <li>✓ Cruzamento livre de choques de horário e compatibilidade de perfil acadêmico</li>
                <li>✓ Assinatura criptográfica SHA-256 garantindo a inviolabilidade dos resultados</li>
              </ul>
            </div>
            <div className="hero-export-action">
              <a
                className="button button-hero-download"
                href={getArtifactUrl("allocation_workbook")}
                download
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="download-icon">
                  <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M7 10L12 15L17 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M12 15V3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Baixar Planilha Final (.XLSX)</span>
              </a>
              <small className="hero-export-note">Download instantâneo · Arquivo nativo Excel</small>
            </div>
          </section>

          {/* INDICADORES DO ARQUIVO PRONTO */}
          {dashboard && (
            <section className="export-summary-section">
              <div className="section-title">
                <div>
                  <span className="step-kicker">RESUMO DO CONTEÚDO</span>
                  <h2>Indicadores consolidados nesta exportação</h2>
                  <p>Dados exatos contidos na planilha que você está baixando.</p>
                </div>
              </div>
              <div className="export-kpi-grid">
                <div className="export-kpi-card highlight">
                  <span>Cobertura Geral</span>
                  <strong>{dashboard.kpis.coverage_pct.toFixed(1)}%</strong>
                  <small>{dashboard.kpis.allocated} alocadas de {dashboard.kpis.transmissions} transmissões</small>
                </div>
                <div className="export-kpi-card">
                  <span>Corpo Docente Ativo</span>
                  <strong>{dashboard.kpis.active_teachers} docentes</strong>
                  <small>Capacidade letiva bruta: {dashboard.kpis.active_teaching_capacity_hours}h</small>
                </div>
                <div className="export-kpi-card">
                  <span>Lacunas Remanescentes</span>
                  <strong>{dashboard.kpis.unassigned} ofertas</strong>
                  <small>Detalhadas na aba "Não Alocadas" do Excel</small>
                </div>
                <div className="export-kpi-card">
                  <span>Taxa de Uso Docente</span>
                  <strong>{dashboard.kpis.teacher_use_pct.toFixed(1)}%</strong>
                  <small>{dashboard.kpis.used_teachers} docentes com alocação ativa</small>
                </div>
              </div>
            </section>
          )}

          {/* PACOTES DE AUDITORIA E CONFORMIDADE */}
          <section className="audit-packages-section">
            <div className="section-title">
              <div>
                <span className="step-kicker">GOVERNANÇA & AUDITORIA</span>
                <h2>Pacotes Complementares de Conformidade</h2>
                <p>Relatórios estruturados e arquivos de comprovação técnica para coordenações e comissões de avaliação.</p>
              </div>
            </div>
            <div className="audit-packages-grid">
              <div className="audit-card">
                <div className="audit-card-header">
                  <span className="audit-badge">METRADADOS JSON</span>
                  <h3>Resumo Executivo</h3>
                </div>
                <p>Arquivo JSON estruturado com todos os KPIs de cobertura, estatísticas de duplo vínculo e indicadores consolidados para integração com BI e painéis institucionais.</p>
                <div className="audit-card-footer">
                  <a className="button button-outline" href={getArtifactUrl("allocation_summary")} download>
                    Baixar Resumo (.JSON)
                  </a>
                </div>
              </div>

              <div className="audit-card">
                <div className="audit-card-header">
                  <span className="audit-badge">AUDITORIA SHA-256</span>
                  <h3>Manifesto de Integridade</h3>
                </div>
                <p>Arquivo de certificação criptográfica contendo os hashes SHA-256 de todas as entradas, tabelas intermediárias e saídas finais computadas pelo motor de alocação.</p>
                <div className="audit-card-footer">
                  <a className="button button-outline" href={getArtifactUrl("manifest")} download>
                    Baixar Manifesto (.JSON)
                  </a>
                </div>
              </div>

              <div className="audit-card">
                <div className="audit-card-header">
                  <span className="audit-badge">LOG OPERACIONAL</span>
                  <h3>Registro de Diagnóstico</h3>
                </div>
                <p>Trilha temporal cronológica detalhando as fases de validação da base, otimização heurística, otimização exata e tempos computacionais de convergência.</p>
                <div className="audit-card-footer">
                  <a className="button button-outline" href={getArtifactUrl("status")} download>
                    Baixar Diagnóstico (.JSON)
                  </a>
                </div>
              </div>

              {selectedJob.upload_id && (
                <div className="audit-card">
                  <div className="audit-card-header">
                    <span className="audit-badge">BASE DE ENTRADA</span>
                    <h3>Relatório de Pendências</h3>
                  </div>
                  <p>Planilha de diagnóstico (.XLSX) apontando potenciais inconsistências, homônimos, choques pré-existentes ou perfis incompletos detectados na validação inicial da base.</p>
                  <div className="audit-card-footer">
                    <a className="button button-outline" href={`/api/uploads/${selectedJob.upload_id}/validation.xlsx`} download>
                      Baixar Pendências (.XLSX)
                    </a>
                  </div>
                </div>
              )}
            </div>
          </section>

          <footer className="source-note">
            <span>Garantia OPTIMAL</span>
            Todos os arquivos exportados são gerados localmente e verificados pelo sistema antiviolação do projeto antes da disponibilização para download.
            {selectedJob && <> Contexto ativo: {jobContextLabel(selectedJob)}.</>}
          </footer>
        </>
      )}
    </div>
  );
}
