import type { Job } from "./types";

export function formatJobDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function jobContextLabel(job: Job) {
  if (job.kind === "SCENARIO") return job.is_official ? "OFICIAL · CENÁRIO" : "SIMULAÇÃO";
  return job.is_official ? "OFICIAL · RODADA-BASE" : "RODADA-BASE";
}

export function formatAnalysisJobLabel(job: Job) {
  const round = job.round ?? "Sem número de rodada";
  return `${jobContextLabel(job)} · Módulo ${job.module} · ${round} · ${formatJobDate(job.created_at)} · ${job.filename}`;
}
