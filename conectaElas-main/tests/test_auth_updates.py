import os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as project

class AuthUpdateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=project.DB
  project.DB=Path(self.temp.name)/'auth.db';project.init_db()
  project.app.config.update(TESTING=True,SECRET_KEY='test-secret',SESSION_COOKIE_SECURE=False)
  self.client=project.app.test_client()
 def tearDown(self):
  project.DB=self.old;self.temp.cleanup()
 def register(self,email):
  return self.client.post('/auth/register',json={'name':'Teste','email':email,'password':'SenhaTeste12345'})
 def test_logout_switch_and_replay(self):
  self.assertEqual(self.register('a@example.com').status_code,200)
  old=self.client.get_cookie('session').value
  self.assertEqual(self.client.post('/auth/logout',data={'logout':'1'}).status_code,303)
  self.client.set_cookie('session',old)
  self.assertIsNone(self.client.get('/data/me').json['user'])
  self.assertEqual(self.register('b@example.com').status_code,200)
  self.assertEqual(self.client.get('/data/me').json['user']['email'],'b@example.com')
 @patch.dict(os.environ,{'RESEND_API_KEY':'test','MAIL_FROM':'test@example.com','PUBLIC_BASE_URL':'https://example.com'})
 @patch('app.send_auth_email')
 def test_verify_and_reset(self,send):
  self.assertEqual(self.register('a@example.com').status_code,200)
  token=send.call_args.args[2].split('verify_token=')[1].split()[0]
  self.assertEqual(self.client.post('/auth/email/verify',json={'token':token}).status_code,200)
  self.assertEqual(self.client.get('/data/me').json['user']['email_verified'],1)
  self.assertEqual(self.client.post('/auth/email/verify',json={'token':token}).status_code,400)
  self.client.post('/auth/password/forgot',json={'email':'a@example.com'})
  token=send.call_args.args[2].split('reset_token=')[1].split()[0]
  self.assertEqual(self.client.post('/auth/password/reset',json={'token':token,'password':'NovaSenha123456'}).status_code,200)
  self.assertIsNone(self.client.get('/data/me').json['user'])
  self.assertEqual(self.client.post('/auth/login',json={'email':'a@example.com','password':'NovaSenha123456'}).status_code,200)
