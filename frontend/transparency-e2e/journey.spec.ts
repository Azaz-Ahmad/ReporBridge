import {test,expect,type Page} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {join} from 'node:path';
async function signIn(page:Page,role:'coordinator'|'reviewer'){
 if(process.env.TRANSPARENCY_VIDEO==='true'){await page.evaluate(token=>sessionStorage.setItem('reprobridge-token',token),process.env['E2E_'+role.toUpperCase()+'_TOKEN']!);await page.reload();await expect(page.getByRole('navigation')).toBeVisible();return;}
 await page.getByLabel('Demo access token').fill(process.env['E2E_'+role.toUpperCase()+'_TOKEN']!);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByRole('navigation')).toBeVisible();
}
test('transparent synthetic journey: detect, documents, draft, edit, approve, close and payload',async({page},testInfo)=>{
 const coordinator={Authorization:'Bearer '+process.env.E2E_COORDINATOR_TOKEN!};
 const reviewer={Authorization:'Bearer '+process.env.E2E_REVIEWER_TOKEN!};
 const captures=process.env.TRANSPARENCY_CAPTURE_DIR;const recording=process.env.TRANSPARENCY_VIDEO==='true';let began=Date.now();let trimStartSeconds=0;
 const hold=async(second:number)=>{if(recording){const remaining=began+second*1000-Date.now();if(remaining>0)await page.waitForTimeout(remaining);}};
 if(recording)await page.addInitScript(token=>{if(!sessionStorage.getItem('reprobridge-token'))sessionStorage.setItem('reprobridge-token',token);},process.env.E2E_COORDINATOR_TOKEN!);
 async function capture(name:string){if(!captures)return;await mkdir(captures,{recursive:true});
 const visible=await page.locator('body').innerText();expect(visible).not.toMatch(/2017|Age 22|six innovations|seven innovations|182\/182|Facility not recorded/i);if(!name.includes('payload'))expect(visible).not.toContain('CITATION_PENDING_CLINICAL_CONFIRMATION');
 for(const width of (recording?[1920]:[1366,1920])){await page.setViewportSize({width,height:width===1366?768:1080});await page.evaluate(()=>document.fonts.ready.then(()=>undefined));
 if(name.includes('draft')||name.includes('clinician-review'))await page.getByRole('heading',{name:'Original and clinician-authored draft',exact:true}).scrollIntoViewIfNeeded();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal page overflow at '+width).toBe(true);
 await page.screenshot({path:join(captures,name+'-'+width+'.png'),fullPage:false,animations:'disabled'});}
 await page.setViewportSize({width:1920,height:1080});}

 async function post(path:string,data:unknown={},headers=coordinator){const response=await page.request.post('/api'+path,{headers,data});expect(response.ok(),path+' '+response.status()).toBeTruthy();return response.json();}
 await post('/v1/tsp/demo/reset');await post('/demo/jury-seed');
 const windowBefore=await(await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:coordinator})).json();expect(windowBefore.status).toBe('IN_WINDOW');
 await page.goto('/');await signIn(page,'coordinator');await expect(page.getByLabel('Demo clock banner')).toContainText('As of 2026-11-22');await expect(page.getByLabel('Demo as-of date',{exact:true})).toHaveValue('2026-11-22');await expect(page.locator('.jury-kpis > div').nth(1).locator('strong')).toHaveText('3');await expect(page.getByRole('cell',{name:/Lina Omar/})).toBeVisible();if(recording){trimStartSeconds=(Date.now()-began)/1000;began=Date.now();}await capture('01-population');await hold(8);
 await page.goto('/workspace?patient=demo-amira');
 const receive=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/history-handoff/patients/demo-amira/receive');
 await page.getByRole('button',{name:'Receive earlier Hospital A records',exact:true}).click();expect((await receive).ok()).toBeTruthy();
 const candidates=await(await page.request.get('/api/v1/historical-candidates/patients/demo-amira',{headers:coordinator})).json();expect(candidates).toHaveLength(1);const candidate=candidates[0];
 await page.goto('/passport?candidate='+candidate.id+'&patient=demo-amira');await expect(page.getByText('Candidate: needs clinician confirmation',{exact:true})).toBeVisible();await capture('03-candidate-passport');await hold(18);
 await page.getByRole('link',{name:'Read source documents',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Source documents',exact:true})).toBeVisible();await page.getByRole('button',{name:/Adolescent clinic note/}).click();
 await expect(page.locator('.stored-document mark')).toHaveText('documented PCOS diagnosis');
 const docs=await(await page.request.get('/api/v1/source-documents/patients/demo-amira',{headers:coordinator})).json();expect(docs).toHaveLength(4);expect(docs.every((d:{date:string})=>!!d.date)).toBe(true);
 expect((await page.getByLabel('Full stored document text').textContent())).toBe(docs.find((d:{simulated:boolean})=>d.simulated).text);
 await expect(page.locator('nav a[aria-current="page"]')).toContainText('05');await capture('05-source-documents');
 for(const width of (recording?[1920]:[1366,1920])){await page.setViewportSize({width,height:width===1366?768:1080});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await capture('05-source-documents-'+width);}
 await page.setViewportSize({width:1920,height:1080});await hold(30);
 await page.goto('/workspace?patient=demo-amira');
 const explanationResponse=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/history-handoff/patients/demo-amira/explanations');
 await page.getByRole('button',{name:'Explain cited earlier record',exact:true}).click();const run=await(await explanationResponse).json();
 expect(run.detail.explanation.accepted,JSON.stringify(run.detail.explanation)).toBe(true);expect(run.detail.usage.model_calls).toBe(0);
 expect(run.detail.explanation.text).not.toContain('IN_WINDOW');expect(run.detail.explanation.text).not.toContain('inclusive');
 await post('/v1/agents/clinical-evidence/runs/'+run.id+'/submit');
 await page.goto('/resolution');await page.getByRole('button',{name:'Sign out',exact:true}).click();await signIn(page,'reviewer');
 await expect(page.getByRole('heading',{name:'Care-resolution center',exact:true})).toBeVisible();
 await page.getByRole('combobox',{name:'Investigation run',exact:true}).selectOption(run.id);
 await page.getByRole('button',{name:'Edit draft',exact:true}).click();await expect(page.getByLabel('Original immutable draft')).toHaveText(run.detail.explanation.text);
 const authored=run.detail.explanation.text+' Clinician-authored coordination note: review source documents with the responsible team.';
 await page.getByLabel('Clinician-authored draft',{exact:true}).fill(authored);
 const saveResponse=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/review-drafts/'+run.id+'/versions');
 await page.getByRole('button',{name:'Save clinician-authored version',exact:true}).click();expect((await saveResponse).ok()).toBeTruthy();
 await expect(page.getByLabel('Clinician-authored draft',{exact:true})).toHaveValue(authored);await expect(page.getByLabel('Calculator-owned windows')).toContainText(windowBefore.windows[0].window_end);
 await expect(page.locator('nav a[aria-current="page"]')).toContainText('04');await capture('04-editable-draft');await hold(48);
 await page.getByLabel('Edited draft review note',{exact:true}).fill('Synthetic clinician approved this exact authored version; closure requires its separate evidence and approval.');
 const editedApproval=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/review-drafts/'+run.id+'/approve');
 await page.getByRole('button',{name:'Approve clinician-authored draft',exact:true}).click();expect((await editedApproval).ok()).toBeTruthy();
 await expect(page.getByText(/Clinician-authored version approved/)).toBeVisible();await capture('04-clinician-review');await hold(58);
 await page.goto('/passport?candidate='+candidate.id+'&patient=demo-amira');
 await page.getByLabel('Candidate review rationale').fill('Synthetic clinician confirms coordination review from the cited Hospital A record; no risk judgement.');
 const candidateApproval=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/historical-candidates/'+candidate.id+'/review');
 await page.getByRole('button',{name:'Confirm historical candidate',exact:true}).click();const confirmed=await(await candidateApproval).json();expect(confirmed.status).toBe('confirmed');const obligation=confirmed.obligation_id;
 expect((await page.request.post('/api/obligations/'+obligation+'/close',{headers:coordinator})).status()).toBe(409);
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await signIn(page,'coordinator');
 await page.goto('/audit');await page.getByLabel('Completion evidence obligation',{exact:true}).selectOption(obligation);
 await page.getByRole('button',{name:'Add verified evidence',exact:true}).click();await expect(page.getByRole('status')).toContainText('Verified fixture submitted');
 await page.goto('/passport?obligation='+obligation);const routed=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/obligations/'+obligation+'/agent');await page.getByRole('button',{name:'Run care-resolution agent',exact:true}).click();expect((await routed).ok()).toBeTruthy();await expect(page.getByRole('status')).toContainText('Coordination action routed for review');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await signIn(page,'reviewer');await page.goto('/resolution?obligation='+obligation);
 await page.getByLabel('Review note',{exact:true}).fill('Synthetic final reconciliation evidence reviewed separately from the clinician-authored draft.');
 const clinicalApproval=page.waitForResponse(r=>r.request().method()==='POST'&&/\/api\/tasks\/[^/]+\/review$/.test(new URL(r.url()).pathname));
 await page.getByRole('button',{name:'Approve',exact:true}).click();expect((await clinicalApproval).ok()).toBeTruthy();
 const stillOpen=await(await page.request.get('/api/snapshot',{headers:coordinator})).json();expect(stillOpen.clinical_obligations.find((o:any)=>o.id===obligation).status).toBe('open');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await signIn(page,'coordinator');await page.goto('/passport?obligation='+obligation);
 const closed=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/obligations/'+obligation+'/close');
 await page.getByRole('button',{name:'Verify closure',exact:true}).click();expect((await closed).ok()).toBeTruthy();await expect(page.getByRole('status')).toContainText('Closure verified');await capture('03-verified-closure');await hold(76);
 const after=await(await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:coordinator})).json();expect(after).toEqual(windowBefore);
 await page.goto('/workspace?patient=demo-amira');await expect(page.getByRole('heading',{name:'Amira Haddad',exact:true})).toBeVisible();await capture('02-workspace');
 await page.goto('/audit');await page.getByLabel('Payload patient',{exact:true}).selectOption('demo-amira');await page.getByRole('tab',{name:'Model payload',exact:true}).click();
 await expect(page.getByLabel('Captured request payload')).toBeVisible();await expect(page.getByText(/replayed — original recorded call/)).toBeVisible();
 await expect(page.getByLabel('Captured request payload')).toContainText('CITATION_PENDING_CLINICAL_CONFIRMATION');
 const body=await page.getByLabel('Captured request payload').textContent();expect(body).not.toMatch(/sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+/);expect(body?.toLowerCase()).not.toContain('authorization');
 await expect(page.locator('nav a[aria-current="page"]')).toContainText('06');await capture('06-model-payload');
 for(const width of (recording?[1920]:[1366,1920])){await page.setViewportSize({width,height:width===1366?768:1080});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await capture('06-model-payload-'+width);}
 if(captures&&!recording){await page.getByLabel('Captured request payload').scrollIntoViewIfNeeded();await capture('06-actual-request-response');}
 if(recording){expect(Date.now()-began,'Storyboard reaches payload view before the final hold').toBeLessThan(89000);await hold(93);}
 if(recording)await testInfo.attach('storyboard timing',{body:JSON.stringify({trim_start_seconds:trimStartSeconds,story_seconds:93}),contentType:'application/json'});
 await testInfo.attach('transparent synthetic journey',{body:JSON.stringify({run_id:run.id,candidate_id:candidate.id,obligation_id:obligation,mode:'replay',live_model_calls:0}),contentType:'application/json'});
});
