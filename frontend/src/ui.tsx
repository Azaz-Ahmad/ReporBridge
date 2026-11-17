import { Slot } from '@radix-ui/react-slot';
import type { ComponentProps, ReactNode } from 'react';
import { CircleAlert, ShieldCheck } from 'lucide-react';
import { label } from './types';

export function Button({ asChild, variant = 'primary', className = '', ...props }:
  ComponentProps<'button'> & { asChild?: boolean; variant?: 'primary' | 'outline' | 'danger' }) {
  const Element = asChild ? Slot : 'button';
  return <Element className={'button ' + variant + ' ' + className} {...props} />;
}

export function Status({ value }: { value: string }) {
  const color = ['closed', 'approve', 'available', 'evidence_available', 'verified', 'ready', 'completed'].includes(value)
    ? 'green' : ['pending', 'open', 'request_evidence', 'missing_closure_evidence', 'waiting_for_review', 'escalated'].includes(value) ? 'amber'
      : ['reject', 'blocked', 'failed', 'conflicting_or_unqualified_evidence'].includes(value) ? 'rose' : 'neutral';
  return <span className={'pill ' + color}><span />{label(value)}</span>;
}

export function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <section className="panel"><div className="panel-heading"><h2>{title}</h2>{action}</div>{children}</section>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Feedback({ message, error }: { message: string; error?: boolean }) {
  return <div className={'feedback ' + (error ? 'error' : '')} role={error ? 'alert' : 'status'}>
    {error ? <CircleAlert size={18} /> : <ShieldCheck size={18} />}{message}
  </div>;
}
