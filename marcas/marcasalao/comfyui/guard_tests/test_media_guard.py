import importlib.util
import json
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
try:import marcasalao_media_guard as g
except ImportError:g=None

class GuardTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(g,'Guard obrigatório ainda ausente')
 def test_manual_image_has_no_comfy_provenance(self):
  with tempfile.TemporaryDirectory() as t:
   Path(t,'manifest.json').write_text(json.dumps({'visual_standard':'quadrado-compartilhado-ia-v4','images':[{'file':'manual.png','sha256':'fake'}]}))
   with self.assertRaises(ValueError):g.validate_package(Path(t),'not-a-prompt',lambda p:{})
 def test_nested_mcp_manual_media_is_blocked(self):
  payload={'profile':'default','tool_name':'tool_call','tool_input':{'calls':[{'name':'mcp__postiz__integrationSchedulePostTool','arguments':{'socialPost':[{'integrationId':'cmvbegwql0001msbhvdpjy0in','type':'draft','postsAndComments':[{'attachments':['https://postiz.swnsolucoes.com.br/uploads/manual.png']}]}]}}]}}
  self.assertEqual(g.check_tool(payload,lambda u:False,lambda c,u:False)['action'],'block')
 def test_registered_image_allows_first_draft_but_blocks_duplicate(self):
  p={'profile':'default','tool_name':'mcp__postiz__integrationSchedulePostTool','tool_input':{'socialPost':[{'integrationId':'cmvbegwql0001msbhvdpjy0in','type':'draft','postsAndComments':[{'attachments':['https://postiz.swnsolucoes.com.br/uploads/valid.png']}]}]}}
  self.assertEqual(g.check_tool(p,lambda u:True,lambda c,u:False),{})
  self.assertEqual(g.check_tool(p,lambda u:True,lambda c,u:True)['action'],'block')
 def test_other_profile_and_readonly_tools_unchanged(self):
  self.assertEqual(g.check_tool({'profile':'multitrackhub-marketing','tool_name':'terminal','tool_input':{'command':'postiz upload /tmp/a.png'}},lambda u:False,lambda c,u:True),{})
  self.assertEqual(g.check_tool({'profile':'default','tool_name':'terminal','tool_input':{'command':'postiz posts:list'}},lambda u:False,lambda c,u:False),{})
 def test_direct_upload_and_pillow_design_blocked(self):
  for cmd in ['postiz upload /tmp/manual.png',"python3 -c 'from PIL import ImageDraw; ImageDraw.Draw(x)'",'postiz posts:create -t draft']:
   self.assertEqual(g.check_tool({'profile':'default','tool_name':'terminal','tool_input':{'command':cmd}},lambda u:True,lambda c,u:False)['action'],'block')
 def test_valid_package_accepts_only_server_image_and_rejects_tamper(self):
  import hashlib,copy
  pid='11111111-1111-1111-1111-111111111111'
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);raw=b'authoritative-comfy-image';(root/'arte.png').write_bytes(raw)
   caps={}
   for n in ['facebook','instagram']:
    data=(n+' caption\n').encode();(root/(n+'.txt')).write_bytes(data);caps[n]={'file':n+'.txt','sha256':hashlib.sha256(data).hexdigest()}
   manifest={'visual_standard':'quadrado-compartilhado-ia-v4','publication_authorized':False,'bundle':'marcasalao/test/run','images':[{'file':'arte.png','sha256':hashlib.sha256(raw).hexdigest(),'format':'quadrado','width':1080,'height':1080}],'captions':caps}
   (root/'manifest.json').write_text(json.dumps(manifest))
   record={'status':{'status_str':'success'},'prompt':[None,None,{'2':{'class_type':'MarcaSalaoArteIA','inputs':{'rede':'compartilhado','formato':'quadrado'}}}],'outputs':{'3':{'text':[json.dumps(manifest)]}}}
   def fetch(path,binary=False):return raw if binary else {pid:record}
   self.assertEqual(g.validate_package(root,pid,fetch)['sha256'],hashlib.sha256(raw).hexdigest())
   (root/'arte.png').write_bytes(b'locally-redrawn')
   with self.assertRaises(ValueError):g.validate_package(root,pid,fetch)
   (root/'arte.png').write_bytes(raw);record['prompt'][2]['2']['class_type']='MarcaSalaoGeminiCenario'
   with self.assertRaises(ValueError):g.validate_package(root,pid,fetch)

 def test_duplicate_in_same_payload_and_nested_batch_is_blocked(self):
  post={'integrationId':'cmvbegwql0001msbhvdpjy0in','type':'draft','postsAndComments':[{'attachments':['https://postiz.swnsolucoes.com.br/uploads/valid.png']}]}
  for name,args in [('mcp__postiz__integrationSchedulePostTool',{'socialPost':[post,post]}),('tool_call',{'calls':[{'name':'mcp__postiz__integrationSchedulePostTool','arguments':{'socialPost':[post]}},{'name':'mcp__postiz__integrationSchedulePostTool','arguments':{'socialPost':[post]}}]})]:
   self.assertEqual(g.check_tool({'profile':'default','tool_name':name,'tool_input':args},lambda u:True,lambda c,u:False).get('action'),'block')

 def test_upload_reuses_media_even_with_another_state_file(self):
  import hashlib,subprocess
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);image=root/'arte.png';image.write_bytes(b'valid-comfy-output')
   proof={'image_path':str(image),'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'prompt_id':'11111111-1111-1111-1111-111111111111','package':str(root),'standard':'quadrado-compartilhado-ia-v4'}
   (root/'secrets/postiz').mkdir(parents=True);(root/'secrets/postiz/api-key').write_text('fixture-not-a-secret')
   process=subprocess.CompletedProcess([],0,'{"id":"media-one","path":"https://postiz.swnsolucoes.com.br/uploads/valid.png"}','')
   with patch.object(g,'HOME',root),patch.object(g,'REGISTRY',root/'registry'),patch.object(g,'validate_package',return_value=proof.copy()),patch.object(g.subprocess,'run',return_value=process) as sender:
    first=g.upload(root,proof['prompt_id'],root/'state1.json');second=g.upload(root,proof['prompt_id'],root/'state2.json')
    self.assertEqual(first['media']['id'],'media-one');self.assertEqual(second['media']['id'],'media-one')
    self.assertEqual(sender.call_count,1)
    self.assertEqual(json.loads((root/'state2.json').read_text())['status'],'complete')

if __name__=='__main__':unittest.main()
