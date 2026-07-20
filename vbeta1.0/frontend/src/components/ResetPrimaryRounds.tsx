import { useEffect, useRef, useState } from "react";
import { resetPrimaryJobs } from "../api";

type ResetPrimaryRoundsProps = {
  disabled?: boolean;
};

export default function ResetPrimaryRounds({ disabled = false }: ResetPrimaryRoundsProps) {
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const busyRef = useRef(false);

  useEffect(() => { busyRef.current = busy; }, [busy]);

  useEffect(() => {
    if (!confirmationOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busyRef.current) {
        setConfirmationOpen(false);
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled)"));
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
  }, [confirmationOpen]);

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
        aria-controls="primary-reset-dialog"
        onClick={() => {
          setError("");
          setConfirmationOpen((current) => !current);
        }}
      >
        Zerar rodadas-base
      </button>

      {confirmationOpen && (
        <div ref={dialogRef} id="primary-reset-dialog" className="primary-reset-confirmation" role="dialog" aria-modal="true" aria-labelledby="primary-reset-title" aria-describedby="primary-reset-description">
          <span className="step-kicker">CONFIRMAÇÃO</span>
          <strong id="primary-reset-title">Zerar rodadas-base</strong>
          <p id="primary-reset-description">Os cenários vinculados às rodadas removidas também serão excluídos. Esta ação não pode ser desfeita.</p>
          <div className="scenario-reset-actions">
            <button ref={cancelRef} type="button" className="button secondary" disabled={busy} onClick={() => setConfirmationOpen(false)}>Cancelar</button>
            <button type="button" className="button secondary danger" disabled={busy} onClick={() => void handleReset("latest")}>Somente o último</button>
            <button type="button" className="button primary danger" disabled={busy} onClick={() => void handleReset("all")}>Zerar todos</button>
          </div>
        </div>
      )}

      {error && <small className="primary-reset-error" role="alert">{error}</small>}
    </div>
  );
}
