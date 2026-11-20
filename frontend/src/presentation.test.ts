import {expect,test} from 'vitest';
import {PRODUCT_NAME,displayText,displayJson,demoPatient} from './presentation';
test('canonical product name',()=>expect(PRODUCT_NAME).toBe('Ajyra AI - ReproBridge'));
test('masks the pending placeholder only for display',()=>{const raw='CITATION_PENDING_CLINICAL_CONFIRMATION';expect(displayText(raw)).toBe('pending clinical confirmation');expect(raw).toBe('CITATION_PENDING_CLINICAL_CONFIRMATION');});
test('masks placeholders nested in technical traces',()=>expect(displayJson({trace:['CITATION_PENDING_CLINICAL_CONFIRMATION']})).not.toContain('CITATION_PENDING'));
test('uses human demo patient names and a safe unknown label',()=>{expect(demoPatient('demo-amira')).toBe('Amira Haddad');expect(demoPatient('private-id')).toBe('Synthetic patient');});
