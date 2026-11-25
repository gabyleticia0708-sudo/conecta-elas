import os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as project
import lia_ai


class LiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        project.DB = Path(cls.tmp.name) / 'lia.sqlite'
        project.init_db(); project.lia_init()
        project.app.config.update(TESTING=True, SECRET_KEY='test-secret')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.client = project.app.test_client()
        lia_ai._calls.clear()
        self.env = mock.patch.dict(os.environ, {'OLLAMA_URL':'http://127.0.0.1:11434','OLLAMA_MODEL':'llama3.2:1b','OLLAMA_API_KEY':''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def login(self, email='lia@example.com'):
        r = self.client.post('/auth/register', json={'name': 'Aluna LIA', 'email': email, 'password': 'SenhaSegura123'})
        self.assertEqual(r.status_code, 200)

    def test_pages_load_with_lia_and_accessibility_assets(self):
        for path in ['/lia', '/tutora', '/dashboard', '/cursos', '/laboratorio']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            html = r.get_data(as_text=True)
            self.assertIn('/static/a11y.js', html); self.assertIn('/static/lia.js', html)
            self.assertIn('/static/a11y.css', html)

    def test_requires_login(self):
        self.assertEqual(self.client.post('/data/lia/chat', json={'question': 'oi'}).status_code, 401)
        self.assertEqual(self.client.get('/data/lia/history').status_code, 401)
        self.assertEqual(self.client.delete('/data/lia/history').status_code, 401)

    def test_no_key_gives_honest_error_and_no_fake_answer(self):
        self.login('semchave@example.com')
        os.environ['OLLAMA_URL'] = 'https://ollama.com'
        r = self.client.post('/data/lia/chat', json={'question': 'O que é uma variável?'})
        self.assertEqual(r.status_code, 503)
        self.assertIn('OLLAMA_API_KEY', r.get_json()['error'])
        self.assertEqual(self.client.get('/data/lia/history').get_json()['messages'], [])

    def test_chat_history_clear_and_context_without_answer_key(self):
        self.login('chat@example.com')
        os.environ['OLLAMA_API_KEY'] = 'chave-de-teste'
        lesson = project.COURSES['logic']['lessons'][0]
        captured = {}

        def fake(system, messages):
            captured['system'] = system; captured['messages'] = messages
            return 'Vamos pensar juntas! Qual é a entrada do problema?', None, None

        with mock.patch.object(lia_ai, 'ask_lia', fake):
            r = self.client.post('/data/lia/chat', json={'question': 'Me ajude', 'level': 'iniciante', 'mode': 'hint', 'lesson_id': lesson['id'], 'code': 'x = 1', 'language': 'python'})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertIn('Pensamento computacional', captured['system'])
        self.assertNotIn(str(lesson['options'][int(lesson['correct'])]), captured['system'])  # gabarito nunca vai para a IA
        self.assertIn('x = 1', captured['messages'][-1]['content'])
        self.assertIn('NÃO entregue a solução', captured['system'])
        h = self.client.get('/data/lia/history').get_json()['messages']
        self.assertEqual([m['role'] for m in h], ['user', 'assistant'])
        self.assertEqual(h[0]['lesson_id'], lesson['id'])
        # a segunda pergunta envia o histórico
        with mock.patch.object(lia_ai, 'ask_lia', fake):
            self.client.post('/data/lia/chat', json={'question': 'E agora?'})
        self.assertEqual(len(captured['messages']), 3)
        self.assertEqual(captured['messages'][0]['role'], 'user')
        self.assertEqual(self.client.delete('/data/lia/history').status_code, 200)
        self.assertEqual(self.client.get('/data/lia/history').get_json()['messages'], [])

    def test_validation_and_privacy_between_users(self):
        self.login('a@example.com')
        os.environ['OLLAMA_API_KEY'] = 'chave-de-teste'
        self.assertEqual(self.client.post('/data/lia/chat', json={'question': ''}).status_code, 400)
        self.assertEqual(self.client.post('/data/lia/chat', json={'question': 'oi', 'mode': 'x'}).status_code, 400)
        self.assertEqual(self.client.post('/data/lia/chat', json={'question': 'oi', 'code': 'a' * 7000}).status_code, 400)
        with mock.patch.object(lia_ai, 'ask_lia', lambda s, m: ('ok', None, None)):
            self.client.post('/data/lia/chat', json={'question': 'mensagem da A'})
        other = project.app.test_client()
        other.post('/auth/register', json={'name': 'Aluna B', 'email': 'b@example.com', 'password': 'SenhaSegura123'})
        self.assertEqual(other.get('/data/lia/history').get_json()['messages'], [])

    def test_rate_limit(self):
        self.login('limite@example.com')
        os.environ['OLLAMA_API_KEY'] = 'chave-de-teste'
        with mock.patch.object(lia_ai, 'ask_lia', lambda s, m: ('ok', None, None)):
            codes = [self.client.post('/data/lia/chat', json={'question': 'oi %d' % i}).status_code for i in range(lia_ai.MAX_CALLS + 1)]
        self.assertEqual(codes[-1], 429); self.assertEqual(codes[0], 200)

    def test_api_error_is_not_saved(self):
        self.login('erro@example.com')
        os.environ['OLLAMA_API_KEY'] = 'chave-de-teste'
        with mock.patch.object(lia_ai, 'ask_lia', lambda s, m: (None, 'Falhou', 502)):
            r = self.client.post('/data/lia/chat', json={'question': 'oi'})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(self.client.get('/data/lia/history').get_json()['messages'], [])

    def test_system_prompt_adapts_to_level(self):
        self.assertIn('iniciante', lia_ai.build_system('iniciante', 'explain'))
        self.assertIn('avançada', lia_ai.build_system('avancado', 'explain'))


if __name__ == '__main__':
    unittest.main()
