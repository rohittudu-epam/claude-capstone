export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden="true">
      <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <circle cx="16" cy="16" r="3" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <line x1="10.5" y1="9.5" x2="13.5" y2="14.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="18" cy="7" r="2" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <line x1="16.5" y1="8.5" x2="15" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="2 2" />
    </svg>
  );
}
