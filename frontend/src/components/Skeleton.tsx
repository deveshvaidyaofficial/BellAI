/** Shimmering placeholders shaped like the page, shown while data loads. */
export function Skeleton({ rows = 3, title = true }: { rows?: number; title?: boolean }) {
  return (
    <div className="skeleton" aria-busy="true" aria-label="Loading">
      {title && <span className="sk sk-title" />}
      <div className="card sk-card">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="sk-row">
            <span className="sk sk-line" />
            <span className="sk sk-pill" />
          </div>
        ))}
      </div>
    </div>
  );
}
