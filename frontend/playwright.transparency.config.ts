import {defineConfig} from '@playwright/test';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:[base.webServer];
export default defineConfig({...base,testDir:'./transparency-e2e',timeout:210000,
 use:{...base.use,viewport:{width:1920,height:1080},video:process.env.TRANSPARENCY_VIDEO==='true'?{mode:'on',size:{width:1920,height:1080}}:'off'},
 webServer:servers.map(server=>({...server!,env:{...server!.env,CLINICAL_EVIDENCE_AGENT_ENABLED:'true',LLM_MODE:'replay',OPENAI_API_KEY:'synthetic-test-key-no-live-use'}}))});
