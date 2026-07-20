export type StatusTone = "success" | "warning" | "critical" | "info" | "neutral";

function normalizeStatus(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleUpperCase("pt-BR");
}

export function statusTone(value: string): StatusTone {
  const normalized = normalizeStatus(value);

  if (
    normalized.startsWith("FALHA")
    || ["REPROVADO", "FAILED", "INFEASIBLE", "ERRO", "CANCELADO"].includes(normalized)
  ) return "critical";

  if (["APROVADO_COM_RESSALVAS", "FEASIBLE", "RESSALVA"].includes(normalized)) return "warning";

  if (
    ["APROVADO", "OPTIMAL", "CONCLUIDA", "CONCLUIDO", "HOMOLOGADO", "ATIVO"].includes(normalized)
  ) return "success";

  if (
    normalized === "QUEUED"
    || normalized === "NA FILA"
    || normalized === "EXECUTANDO"
    || normalized === "EM CONFIGURACAO"
    || normalized.startsWith("GRAVANDO")
    || normalized.startsWith("RESOLVENDO")
    || normalized.endsWith("ANDO")
    || normalized.endsWith("ENDO")
  ) return "info";

  return "neutral";
}

export function humanizeStatus(value: string) {
  return value.replaceAll("_", " ");
}

export default function StatusBadge({
  value,
  label,
  className = "",
}: {
  value: string;
  label?: string;
  className?: string;
}) {
  return (
    <span className={`status-badge status-${statusTone(value)} ${className}`.trim()}>
      {label ?? humanizeStatus(value)}
    </span>
  );
}
