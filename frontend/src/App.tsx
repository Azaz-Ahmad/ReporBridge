import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, ArrowRight, ClipboardList, HeartPulse, LayoutDashboard, LogOut, Network, ShieldCheck, Users, Workflow } from 'lucide-react';
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { api } from './api';
import { RoleSwitcher } from './Jury';
import { DemoClock } from './Tsp';
import { AuditScreen, Dashboard, Passport, Resolution, Workspace, type ScreenProps } from './screens';
import { type Role, type Snapshot, label } from './types';
import { Button, Feedback } from './ui';

const links = [
  { path: '/', text: 'Population dashboard', icon: LayoutDashboard },
  { path: '/workspace', text: 'Women’s health workspace', icon: Users },
  { path: '/passport', text: 'Obligation passport', icon: ClipboardList },
  { path: '/resolution', text: 'Care-resolution center', icon: Workflow },
  { path: '/audit', text: 'Evidence & audit', icon: ShieldCheck },
];

function Brand() {
  return <Link to="/" className="brand"><span className="brand-mark"><Activity size={23} /></span>
    <span><strong>ReproBridge</strong><small>AJYRA AI</small></span></Link>;
}

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('reprobridge-token') || '');
  const [draft, setDraft] = useState('');
  const [feedback, setFeedback] = useState<{ message: string; error?: boolean }>();
  const cache = useQueryClient();
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' });
    else window.scrollTo(0, 0);
  }, [pathname, hash]);
  const session = useQuery({
    queryKey: ['session', token], queryFn: () => api<{ role: Role }>(token, '/session'), enabled: !!token,
  });
  const snapshot = useQuery({
    queryKey: ['snapshot', token], queryFn: () => api<Snapshot>(token, '/snapshot'), enabled: !!session.data,
  });
  const signIn = useMutation({
    mutationFn: (secret: string) => api<{ role: Role }>(secret, '/session'),
    onSuccess: (result, secret) => {
      cache.setQueryData(['session', secret], result);
      sessionStorage.setItem('reprobridge-token', secret);
      setToken(secret);
      setDraft('');
      setFeedback(undefined);
    },
  });
  const change = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown; success: string }) => api(token, path, 'POST', body),
    onSuccess: (_, variables) => setFeedback({ message: variables.success }),
    onError: (error) => setFeedback({ message: error.message, error: true }),
    onSettled: () => {
      cache.invalidateQueries({ queryKey: ['snapshot', token] });
      cache.invalidateQueries({ queryKey: ['prevention'] });
      cache.invalidateQueries({ queryKey: ['tsp'] });
      cache.invalidateQueries({ queryKey: ['handoff'] });
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    signIn.mutate(draft.trim());
  };
  const signOut = () => {
    sessionStorage.removeItem('reprobridge-token');
    cache.clear();
    setToken('');
    setFeedback(undefined);
    signIn.reset();
  };
  if (!session.data && !session.isLoading) {
    return <div className="signin"><div className="signin-card">
      <Brand /><span className="eyebrow"><HeartPulse size={16} /> SYNTHETIC DATA — DEMONSTRATION ONLY</span>
      <h1>Care that carries forward.</h1>
      <p>Sign in to follow a synthetic patient from preconception into pregnancy and verify how outstanding care is resolved.</p>
      <form onSubmit={submit}>
        <label htmlFor="token">Demo access token</label>
        <input id="token" type="password" required autoComplete="off" value={draft} onChange={(event) => setDraft(event.target.value)} />
        <Button type="submit" disabled={signIn.isPending || !draft.trim()}>Sign in <ArrowRight size={16} /></Button>
      </form>
      {signIn.error && <Feedback message={signIn.error.message} error />}
      {session.error && !signIn.error && <Feedback message={session.error.message} error />}
    </div></div>;
  }
  const role = session.data?.role;
  const props: ScreenProps | undefined = snapshot.data && role ? {
    data: snapshot.data, role, token, busy: change.isPending,
    busyPath: change.isPending ? change.variables?.path : undefined,
    action: (path, success, body) => {
      setFeedback(undefined);
      change.mutate({ path, success, body });
    },
  } : undefined;
  return <div className="shell">
    <aside className="rail">
      <Brand />
      <nav aria-label="Main navigation">{links.map(({ path, text, icon: Icon }) =>
        <NavLink key={path} to={path} end={path === '/'} onClick={() => setFeedback(undefined)}>
          <Icon size={18} />{text}
        </NavLink>,
      )}</nav>
      {snapshot.data?.patients.some((patient) => patient.id === 'demo-amira') && <Link className="rail-journey" to="/workspace?patient=demo-amira"><HeartPulse size={17} /> Amira’s journey <ArrowRight size={15} /></Link>}
      <div className="rail-note"><Network size={18} /><span>HealthX Ajyal Hackathon<small>22 November 2026</small></span></div>
    </aside>
    <div className="content">
      <header className="app-header"><div className="topbar"><span className="demo-mark"><ShieldCheck size={17} /> SYNTHETIC DATA — DEMONSTRATION ONLY</span>
        <div><RoleSwitcher token={token} onToken={value=>signIn.mutate(value)} /><span className="role">{role ? label(role) : 'Connecting'}</span>
          <button className="icon-button" type="button" title="Sign out" aria-label="Sign out" onClick={signOut}><LogOut size={18} /></button></div>
      </div>
        {role && <div className="tsp-header"><DemoClock token={token} role={role} /></div>}
      </header>
      <main>
        {feedback && <Feedback {...feedback} />}
        {snapshot.error ? <Feedback message={snapshot.error.message} error /> : !props ? <p role="status">Loading workspace…</p> :
          <Routes>
            <Route path="/" element={<Dashboard {...props} />} />
            <Route path="/workspace" element={<Workspace {...props} />} />
            <Route path="/passport" element={<Passport {...props} />} />
            <Route path="/resolution" element={<Resolution {...props} />} />
            <Route path="/audit" element={<AuditScreen {...props} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>}
      </main>
    </div>
  </div>;
}
