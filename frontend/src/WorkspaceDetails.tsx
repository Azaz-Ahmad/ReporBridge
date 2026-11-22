import type { ReactNode } from 'react';

/** A presentation-only disclosure; default callers retain their original markup. */
export function WorkspaceDetails({ compact, title, children }: { compact?: boolean; title: string; children: ReactNode }) {
  return compact ? <details className="workspace-disclosure"><summary>{title}</summary>{children}</details> : <>{children}</>;
}
