import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  children: ReactNode;
  className?: string;
}

export function Sidebar({ children, className }: SidebarProps) {
  return (
    <aside
      className={cn(
        "w-72 flex-shrink-0 border-r border-border-subtle bg-bg-surface overflow-y-auto",
        className,
      )}
    >
      {children}
    </aside>
  );
}

export function SidebarHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("border-b border-border-subtle p-4", className)}>{children}</div>;
}

export function SidebarSection({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("p-4 space-y-3", className)}>{children}</div>;
}

export function SidebarSectionLabel({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="section-label">{children}</h3>
      {count !== undefined && <span className="section-label">{count}</span>}
    </div>
  );
}

export function SidebarRow({
  title,
  meta,
  count,
  selected,
  onClick,
  className,
}: {
  title: string;
  meta?: string;
  count?: number;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-lg border px-3 py-2 text-left transition-all duration-150",
        selected
          ? "border-border-strong bg-bg-elevated shadow-sm"
          : "border-transparent hover:border-border-subtle hover:bg-bg-hover",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className={cn("font-mono text-sm truncate", selected ? "text-accent font-medium" : "text-text-primary")}>
            {title}
          </div>
          {meta && <div className="text-xs text-text-muted mt-0.5">{meta}</div>}
        </div>
        {count !== undefined && (
          <span className="text-xs text-text-secondary font-medium mt-0.5 flex-shrink-0">{count}</span>
        )}
      </div>
    </button>
  );
}

export function SidebarHintBar({ children }: { children: ReactNode }) {
  return (
    <div className="border-t border-border-subtle bg-bg-surface px-4 py-2">
      <div className="flex flex-wrap gap-3 text-xs text-text-muted">{children}</div>
    </div>
  );
}
