import { defineConfig } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdirSync, mkdtempSync } from 'node:fs';
import { resolve } from 'node:path';

const apiPort = Number(process.env.REPROBRIDGE_E2E_API_PORT || 8013);
const webPort = Number(process.env.REPROBRIDGE_E2E_WEB_PORT || 5183);
const backend = resolve('../backend');
const python = resolve('../.venv/Scripts/python.exe');
if (!process.env.E2E_COORDINATOR_TOKEN) {
  for (const role of ['COORDINATOR', 'REVIEWER', 'VIEWER']) {
    process.env['E2E_' + role + '_TOKEN'] = randomBytes(32).toString('hex');
  }
}
mkdirSync('test-results-db', { recursive: true });
const db = mkdtempSync(resolve('test-results-db/run-'));
const serverEnv = {
  CLINICAL_EVIDENCE_AGENT_ENABLED: "false",
  DEMO_MODE: "true",
  REPROBRIDGE_TEST_MODE: "true",
  DATABASE_URL: process.env.REPROBRIDGE_E2E_DATABASE_URL || 'sqlite:///' + resolve(db, 'e2e.db').replaceAll('\\', '/'),
  COORDINATOR_TOKEN: process.env.E2E_COORDINATOR_TOKEN!,
  REVIEWER_TOKEN: process.env.E2E_REVIEWER_TOKEN!,
  VIEWER_TOKEN: process.env.E2E_VIEWER_TOKEN!,
};
execFileSync(python, ['-m', 'alembic', 'upgrade', 'head'], { cwd: backend, env: { ...process.env, ...serverEnv } });

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 45_000,
  use: { actionTimeout: 15_000, baseURL: `http://127.0.0.1:${webPort}`, channel: process.env.E2E_BROWSER_CHANNEL || undefined, trace: 'retain-on-failure' },
  webServer: [
    { command: `..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port ${apiPort}`, cwd: backend,
      url: `http://127.0.0.1:${apiPort}/api/health`, env: serverEnv, timeout: 40_000 },
    { command: `npm.cmd run dev -- --port ${webPort}`, url: `http://127.0.0.1:${webPort}`,
      env: { BACKEND_PROXY: `http://127.0.0.1:${apiPort}` }, timeout: 40_000 },
  ],
});
