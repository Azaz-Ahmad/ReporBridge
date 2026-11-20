"""Synthetic-only release-tool checks; no provider or application requests."""
import json,tempfile,unittest,zipfile
from pathlib import Path
from redact_browser_artifacts import sanitize,tokens_in
class ReleaseArtifacts(unittest.TestCase):
 def test_report_and_trace_redaction_preserves_failure_evidence(self):
  credential='synthetic-throwaway-token-for-unit-test'
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);report=root/'run.json';report.write_text(json.dumps({'config':{'env':{'COORDINATOR_TOKEN':credential}},'stats':{'expected':1,'unexpected':1}}))
   with zipfile.ZipFile(root/'trace.zip','w') as archive:
    archive.writestr('trace.network','Authorization: Bearer '+credential)
    archive.writestr('trace.trace','Failed exact-source assertion; token='+credential)
    archive.writestr('screenshot.png',b'synthetic-image-bytes')
   sanitize(root)
   self.assertNotIn(credential,report.read_text());self.assertEqual(json.loads(report.read_text())['stats'],{'expected':1,'unexpected':1})
   with zipfile.ZipFile(root/'trace.zip') as archive:
    self.assertNotIn(credential.encode(),archive.read('trace.network'));self.assertIn(b'Failed exact-source assertion',archive.read('trace.trace'));self.assertEqual(archive.read('screenshot.png'),b'synthetic-image-bytes')
 def test_usage_values_are_not_credentials(self):
  self.assertEqual(tokens_in({'usage':{'input_tokens':500,'output_tokens':200},'model':'configured-model'}),set())
if __name__=='__main__':unittest.main()
