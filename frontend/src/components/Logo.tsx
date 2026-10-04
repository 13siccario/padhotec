/** Padhotec's mark: three soft discs overlapping, learning where ideas meet. Drawn for this app. */
export function LogoMark({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="shrink-0">
      <g style={{ mixBlendMode: "multiply" }}>
        <circle cx="18" cy="19" r="12" fill="#f3d83a" />
        <circle cx="30" cy="19" r="12" fill="#c9b3ee" />
        <circle cx="24" cy="30" r="12" fill="#9cc6ee" />
      </g>
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-display font-extrabold tracking-tight text-ink ${className}`}>padhotec</span>
  );
}
