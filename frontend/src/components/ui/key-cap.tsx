import * as React from "react";
import { cn } from "@/lib/utils";

export function KeyCap({ children, className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <kbd className={cn("key-cap", className)} {...props}>
      {children}
    </kbd>
  );
}
