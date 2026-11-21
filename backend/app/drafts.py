"""Human-authored review text is separate from calculator and clinical closure state."""
import re
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter,Request
from pydantic import Field
from sqlalchemy import select
from app import service as clinical
from app.clinical.access import authorize,audit_access,fail,now
from app.clinical.contracts import Contract
from app.clinical.normalize import digest
from app.draft_schema import originals,versions,approvals
from app.investigation import service
from app.investigation.contracts import Review
from app.investigation.replay import scrub
from app.prevention import tsp

def source_text(run):
    packet=run['detail'].get('packet') or {};explanation=run['detail'].get('explanation') or {}
    if packet.get('origin')!='model' or packet.get('abstained') or packet.get('grounding_status')=='validation_failed':fail(409,'model_draft_unavailable','There is no accepted model draft to edit. Rule-generated abstention text remains separate.')
    return explanation['text'] if explanation.get('accepted') else packet['summary']

def original(connection,actor,run_id):
    if actor not in {'coordinator','reviewer'}:fail(403,'draft_role_required','Draft review requires Coordinator or Reviewer.')
    run=service.get(connection,actor,run_id);text=source_text(run)
    found=connection.execute(select(originals).where(originals.c.run_id==run_id)).mappings().first()
    if not found:
        if scrub(text)!=text:fail(422,'unsafe_draft','Secret-like text cannot be stored in a review draft.')
        found=dict(run_id=run_id,patient_id=run['patient_id'],text=text,digest=digest(text),created=now(),model=run['detail']['configuration']['model'])
        connection.execute(originals.insert().values(**found))
        clinical.audit(connection,actor,'model_draft_original_recorded',run['patient_id'],run_id=run_id,original_digest=found['digest'])
    elif found['digest']!=digest(text):fail(409,'original_draft_changed','The immutable source draft no longer matches the investigation.')
    return run,dict(found)

def history(connection,run_id):return [dict(row) for row in connection.execute(select(versions).where(versions.c.run_id==run_id).order_by(versions.c.number)).mappings()]

def dates(text):
    result=set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b',text))
    for day,month,year in re.findall(r'\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})\b',text):
        try:result.add(datetime.strptime(day+' '+month+' '+year,'%d %B %Y').date().isoformat())
        except ValueError:pass
    return result

def read(connection,actor,run_id,session_id=None):
    run,record=original(connection,actor,run_id);edits=history(connection,run_id)
    calculator=tsp.patient_window(connection,actor,run['patient_id'],session_id)
    allowed={calculator['as_of']}
    for window in calculator['windows']:
        allowed.update(value[:10] for key,value in window.items() if key in {'window_start','window_end','completion_date'} and value)
    extra=sorted(dates(edits[-1]['text'])-allowed) if edits else []
    approval=connection.execute(select(approvals).where(approvals.c.run_id==run_id)).mappings().first()
    audit_access(connection,authorize(connection,actor,run['patient_id']),'review_draft_viewed')
    return {'original':record,'versions':edits,'approval':dict(approval) if approval else None,'calculator':calculator,
        'date_notice':('Edited text includes dates outside the current calculator result: '+', '.join(extra)+'. These may be historical dates; windows remain calculator-owned. This notice does not block review.') if extra else None,
        'submitted':run['status']=='pending_review','reviewed':bool(run['review'])}

def save(connection,actor,run_id,text,expected_version,session_id=None):
    if actor!='reviewer':fail(403,'reviewer_required','Only Reviewer can author a clinician draft.')
    run,record=original(connection,actor,run_id);edits=history(connection,run_id)
    if run['review']:fail(409,'review_already_recorded','An approved or reviewed draft cannot be edited.')
    if not text.strip() or scrub(text)!=text:fail(422,'unsafe_draft','Provide non-empty clinician text without secret-like values.')
    if expected_version!=(edits[-1]['number'] if edits else 0):fail(409,'stale_draft_version','A newer version exists. Reload before editing.')
    if len(edits)>=50:fail(409,'draft_version_limit','This draft has reached its bounded version history.')
    row=dict(id='draft-'+uuid4().hex,run_id=run_id,number=len(edits)+1,text=text,digest=digest(text),editor=actor,role=actor,created=now())
    connection.execute(versions.insert().values(**row))
    clinical.audit(connection,actor,'clinician_draft_version_recorded',run['patient_id'],run_id=run_id,version_id=row['id'],version=row['number'],text_digest=row['digest'],authorship='clinician-authored')
    return read(connection,actor,run_id,session_id)

def validate_target(connection,run,version_id):
    edits=history(connection,run['id'])
    if edits and (not version_id or edits[-1]['id']!=version_id):fail(409,'edited_version_required','Approve the current clinician-authored version, not the original or an older edit.')

def approve(connection,actor,run_id,version_id,note,session_id=None):
    if actor!='reviewer':fail(403,'reviewer_required','Only Reviewer can approve a clinician draft.')
    run,record=original(connection,actor,run_id);edits=history(connection,run_id)
    if not edits or edits[-1]['id']!=version_id:fail(409,'stale_draft_version','Approval must refer to the latest saved version.')
    previous=connection.execute(select(approvals).where(approvals.c.run_id==run_id)).mappings().first()
    if previous:
        if previous['version_id']==version_id and previous['note']==note:return read(connection,actor,run_id,session_id)
        fail(409,'review_already_recorded','The version-bound decision is immutable.')
    if run['review']:fail(409,'review_already_recorded','An earlier summary decision cannot be rebound to a later edit.')
    if not note.strip():fail(422,'review_note_required','A reviewer note is required.')
    # Existing source-current, grounding and submission checks still run unchanged.
    service.review(connection,actor,run_id,Review(decision='approve_summary',note=note),edited_version_id=version_id)
    row=dict(run_id=run_id,version_id=version_id,version_digest=edits[-1]['digest'],actor=actor,created=now(),note=note)
    connection.execute(approvals.insert().values(**row))
    clinical.audit(connection,actor,'clinician_draft_version_approved',run['patient_id'],run_id=run_id,version_id=version_id,text_digest=edits[-1]['digest'])
    return read(connection,actor,run_id,session_id)

class Edit(Contract):
    text:str=Field(min_length=1,max_length=8000)
    expected_version:int=Field(ge=0,le=50)
class Approve(Contract):
    version_id:str=Field(max_length=100)
    note:str=Field(min_length=1,max_length=500)

def router(Reader,Reviewer,write):
    routes=APIRouter(prefix='/api/v1/review-drafts',tags=['Immutable clinician-authored draft history'])
    @routes.get('/{run_id}')
    def inspect(run_id:str,request:Request,actor:Reader):return write(read,actor,run_id,request.cookies.get('reprobridge-demo-session'))
    @routes.post('/{run_id}/versions')
    def edit(run_id:str,body:Edit,request:Request,actor:Reviewer):return write(save,actor,run_id,body.text,body.expected_version,request.cookies.get('reprobridge-demo-session'))
    @routes.post('/{run_id}/approve')
    def decision(run_id:str,body:Approve,request:Request,actor:Reviewer):return write(approve,actor,run_id,body.version_id,body.note,request.cookies.get('reprobridge-demo-session'))
    return routes
