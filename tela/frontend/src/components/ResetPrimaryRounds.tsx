import { useState } from "react";
import { resetPrimaryJobs } from "../api";

type ResetPrimaryRoundsProps = {
  disabled?: boolean;
};

export default function ResetPrimaryRounds({ disabled = false }: ResetPrimaryRoundsProps) {
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleReset = async (scope: "latest" | "all") => {
    setBusy(true);
    setError("");
    try {
      await resetPrimaryJobs(scope);
      window.location.reload();
    } catch (requestError) {
      setConfirmationOpen(false);
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="primary-reset-control">
      <button
        type="button"
        className="scenario-reset-trigger"
        disabled={disabled || busy}
        aria-expanded={confirmationOpen}
        onClick={() => {
          setError("");
          setConfirmationOpen((current) => !current);
        }}
      >
        Zerar rodadas-base
      </button>

      {confirmationOpen && (
        <div className="primary-reset-confirmation" role="dialog" aria-modal="true" aria-labelledby="primary-reset-title">
          <span className="step-kicker">CONFIRMAÇÃO</span>
          <strong id="primary-reset-title">Zerar rodadas-base</strong>
          <p>Os cenários vinculados às rodadas removidas também serão excluídos.</p>
          <div className="scenario-reset-actions">
            <button type="button" className="button secondary" disabled={busy} onClick={() => setConfirmationOpen(false)}>Cancelar</button>
            <button type="button" className="button secondary danger" disabled={busy} onClick={() => void handleReset("latest")}>Somente o último</button>
            <button type="button" className="button primary danger" disabled={busy} onClick={() => void handleReset("all")}>Zerar todos</button>
          </div>
        </div>
      )}

      {error && <small className="primary-reset-error" role="alert">{error}</small>}
    </div>
  );
}
