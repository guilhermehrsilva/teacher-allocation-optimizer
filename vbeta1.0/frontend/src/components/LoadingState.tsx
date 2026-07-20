export default function LoadingState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="panel loading-state" role="status" aria-live="polite">
      <span className="loading-state-spinner" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </section>
  );
}
