import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  badge?: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, badge, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("border-b border-border-subtle bg-bg-surface px-6 py-4", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="font-mono text-lg font-semibold text-text-primary">{title}</h1>
            {badge && (
              <span className="rounded border border-border-strong bg-bg-elevated px-2 py-0.5 text-xs font-medium text-text-secondary">
                {badge}
              </span>
            )}
          </div>
          {description && <p className="text-sm text-text-secondary">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
