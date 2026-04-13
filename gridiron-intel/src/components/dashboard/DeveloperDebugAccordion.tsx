import { ReactNode } from "react";

export default function DeveloperDebugAccordion({ title = "Developer Debug", children }: { title?: string; children: ReactNode }) {
  return (
    <details className="card-surface rim-light p-4 text-[11px] text-muted-foreground">
      <summary className="cursor-pointer select-none underline underline-offset-2">{title}</summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}

