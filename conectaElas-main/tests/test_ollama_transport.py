import os, json, unittest, sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lia_ai

class OllamaTransport(unittest.TestCase):
    def test_local_and_cloud(self):
        for url, key, model in [('http://127.0.0.1:11434','','llama3.2:1b'),('https://ollama.com','fake-test-key','example-cloud')]:
            with patch.dict(os.environ,{'OLLAMA_URL':url,'OLLAMA_API_KEY':key,'OLLAMA_MODEL':model}), patch('urllib.request.urlopen') as call:
                call.return_value.__enter__.return_value.read.return_value=json.dumps({'message':{'content':'Olá!'}}).encode()
                self.assertEqual(lia_ai.ask_lia('Sistema',[{'role':'user','content':'Oi'}]),('Olá!',None,None))
                req=call.call_args.args[0]
                self.assertEqual(req.full_url,url+'/api/chat')
                self.assertEqual(json.loads(req.data)['model'],model)
                self.assertEqual(req.get_header('Authorization'), 'Bearer '+key if key else None)
    def test_missing_cloud_key(self):
        with patch.dict(os.environ,{'OLLAMA_URL':'https://ollama.com','OLLAMA_API_KEY':'','OLLAMA_MODEL':'example-cloud'}):
            self.assertEqual(lia_ai.ask_lia('Sistema',[])[2],503)
