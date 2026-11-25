import os, sqlite3, json, secrets, hashlib, smtplib, ssl, re, urllib.request, urllib.error
from email.message import EmailMessage
from datetime import timedelta
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, render_template, request, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from flask import url_for, redirect
from xml.sax.saxutils import escape
import assessment_engine as assessments

ROOT=Path(__file__).resolve().parent
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY','local-development-only-change-me')
if os.getenv('FLASK_ENV')=='production' and app.secret_key=='local-development-only-change-me':raise RuntimeError('Configure SECRET_KEY para produção.')
app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(days=7),SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','0')=='1',MAX_CONTENT_LENGTH=1_000_000)
DB=Path(os.getenv('DATABASE_PATH',str(ROOT/'conectas.db')))
DB.parent.mkdir(parents=True,exist_ok=True)
CURRICULUM=json.loads((ROOT/'curriculo.json').read_text(encoding='utf-8'))
COURSES={c['id']:c for c in CURRICULUM['courses']}
LESSONS={l['id']:(c,l) for c in CURRICULUM['courses'] for l in c['lessons']}

def db():
 c=sqlite3.connect(DB,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c

def init_db():
 with db() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS catalog_courses(
    course_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS catalog_lessons(
    lesson_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES catalog_courses(course_id) ON DELETE CASCADE,
    position INTEGER NOT NULL, payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS catalog_lessons_course ON catalog_lessons(course_id,position);
  """)
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS completions(user_id INTEGER NOT NULL REFERENCES users(id),lesson_id TEXT NOT NULL,completed_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,lesson_id));
  CREATE TABLE IF NOT EXISTS quiz_attempts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),lesson_id TEXT NOT NULL,correct INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS certificates(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),course_id TEXT NOT NULL,code TEXT UNIQUE NOT NULL,issued_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,course_id));
  CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,title TEXT NOT NULL,organization TEXT NOT NULL,mode TEXT NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS saved_jobs(user_id INTEGER NOT NULL REFERENCES users(id),job_id INTEGER NOT NULL REFERENCES jobs(id),PRIMARY KEY(user_id,job_id));
  CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS module_assessments(user_id INTEGER NOT NULL REFERENCES users(id),course_id TEXT NOT NULL,module TEXT NOT NULL,passed_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,course_id,module));
  CREATE TABLE IF NOT EXISTS module_practice_submissions(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course_id TEXT NOT NULL,module TEXT NOT NULL,solution TEXT NOT NULL,test_notes TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,course_id,module));
  CREATE TABLE IF NOT EXISTS lesson_practice_submissions(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,lesson_id TEXT NOT NULL,solution TEXT NOT NULL,test_notes TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,lesson_id));
  CREATE TABLE IF NOT EXISTS module_exam_attempts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course_id TEXT NOT NULL,module TEXT NOT NULL,question_count INTEGER NOT NULL,correct_count INTEGER NOT NULL,score REAL NOT NULL,applied_correct INTEGER NOT NULL,passed INTEGER NOT NULL,applied_answer TEXT NOT NULL DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS module_exam_attempts_user_idx ON module_exam_attempts(user_id,course_id,module,id);
  CREATE TABLE IF NOT EXISTS course_favorites(user_id INTEGER NOT NULL REFERENCES users(id),course_id TEXT NOT NULL,PRIMARY KEY(user_id,course_id));
  CREATE TABLE IF NOT EXISTS course_enrollments(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course_id TEXT NOT NULL,started_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,course_id));
  CREATE TABLE IF NOT EXISTS tutor_messages(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, role TEXT NOT NULL CHECK(role IN ('user','assistant')), body TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS tutor_messages_user_idx ON tutor_messages(user_id,id);
  CREATE TABLE IF NOT EXISTS editor_projects(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,title TEXT NOT NULL,language TEXT NOT NULL,code TEXT NOT NULL,lesson_id TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS editor_projects_owner ON editor_projects(user_id,id);
  CREATE TABLE IF NOT EXISTS editor_challenge_attempts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),challenge_id TEXT NOT NULL,passed INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS learning_challenge_attempts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,lesson_id TEXT NOT NULL,answer_index INTEGER NOT NULL,correct INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS learning_challenge_attempts_owner ON learning_challenge_attempts(user_id,lesson_id,id);
  CREATE TABLE IF NOT EXISTS weekly_goals(user_id INTEGER PRIMARY KEY REFERENCES users(id),target INTEGER NOT NULL CHECK(target BETWEEN 1 AND 100),updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS portfolio_items(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,title TEXT NOT NULL,description TEXT NOT NULL,technologies TEXT NOT NULL,project_url TEXT NOT NULL DEFAULT '',course_id TEXT NOT NULL DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS password_reset_tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires_at TEXT NOT NULL,used_at TEXT);
  CREATE TABLE IF NOT EXISTS study_plans(user_id INTEGER PRIMARY KEY REFERENCES users(id),goal TEXT NOT NULL,level TEXT NOT NULL,hours_per_week INTEGER NOT NULL,course_ids TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  c.executescript("""CREATE TABLE IF NOT EXISTS community_comments(id INTEGER PRIMARY KEY,post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS community_likes(post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),PRIMARY KEY(post_id,user_id));
  CREATE TABLE IF NOT EXISTS community_reports(id INTEGER PRIMARY KEY,post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,comment_id INTEGER REFERENCES community_comments(id) ON DELETE CASCADE,reporter_id INTEGER NOT NULL REFERENCES users(id),reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP, CHECK((post_id IS NOT NULL) != (comment_id IS NOT NULL)));
  CREATE TABLE IF NOT EXISTS community_moderators(user_id INTEGER PRIMARY KEY REFERENCES users(id));
  CREATE INDEX IF NOT EXISTS community_reports_status ON community_reports(status);""")
  c.executescript("""CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS admin_course_data(course_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY,admin_id INTEGER REFERENCES users(id),action TEXT NOT NULL,entity TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS certificate_revocations(code TEXT PRIMARY KEY REFERENCES certificates(code),reason TEXT NOT NULL,revoked_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS course_views(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),course_id TEXT NOT NULL,viewed_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS course_views_course ON course_views(course_id);""")

  user_cols={r['name'] for r in c.execute('PRAGMA table_info(users)')}
  if 'account_type' not in user_cols:c.execute("ALTER TABLE users ADD COLUMN account_type TEXT NOT NULL DEFAULT 'student'")
  if 'company_name' not in user_cols:c.execute("ALTER TABLE users ADD COLUMN company_name TEXT NOT NULL DEFAULT ''")
  for col in ('bio','goal','level','interests','occupation','languages','avatar_url'):
   if col not in user_cols:c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
  c.execute("CREATE TABLE IF NOT EXISTS user_preferences(user_id INTEGER PRIMARY KEY REFERENCES users(id), accessibility TEXT NOT NULL DEFAULT '{}', updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
  c.execute("CREATE TABLE IF NOT EXISTS profile_notifications(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, community INTEGER NOT NULL DEFAULT 1, courses INTEGER NOT NULL DEFAULT 1, opportunities INTEGER NOT NULL DEFAULT 1)")
  c.execute("CREATE TABLE IF NOT EXISTS community_blocks(user_id INTEGER NOT NULL REFERENCES users(id), blocked_user_id INTEGER NOT NULL REFERENCES users(id), PRIMARY KEY(user_id,blocked_user_id))")
  c.execute("CREATE TABLE IF NOT EXISTS job_applications(id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,message TEXT NOT NULL DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(job_id,user_id))")
  c.execute("CREATE TABLE IF NOT EXISTS portfolio_highlights(user_id INTEGER NOT NULL REFERENCES users(id),project_id INTEGER NOT NULL REFERENCES portfolio_items(id) ON DELETE CASCADE,PRIMARY KEY(user_id,project_id))")
  pcols={r['name'] for r in c.execute('PRAGMA table_info(portfolio_items)')}
  if 'image_url' not in pcols:c.execute("ALTER TABLE portfolio_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")
  ecols={r['name'] for r in c.execute('PRAGMA table_info(editor_projects)')}
  if 'idea_id' not in ecols:c.execute("ALTER TABLE editor_projects ADD COLUMN idea_id TEXT NOT NULL DEFAULT ''")
  c.execute("CREATE TABLE IF NOT EXISTS community_connections(user_id INTEGER NOT NULL REFERENCES users(id),peer_id INTEGER NOT NULL REFERENCES users(id),created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,peer_id))")
  # PASSO 10: conexões seguras, sem divulgação pública de dados pessoais.
  c.executescript("""CREATE TABLE IF NOT EXISTS community_profiles(
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    visible INTEGER NOT NULL DEFAULT 0, bio TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT '', skills TEXT NOT NULL DEFAULT '',
    mentorship INTEGER NOT NULL DEFAULT 0, collaboration INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS community_requests(
    id INTEGER PRIMARY KEY, sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK(kind IN ('mentoria','colaboracao')),
    message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS community_notifications(
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS community_notifications_owner ON community_notifications(user_id,is_read,id);
  CREATE INDEX IF NOT EXISTS community_requests_recipient ON community_requests(recipient_id,status);
  """)
  # PASSO 9: configurações privadas e link público aleatório por usuária.
  c.execute("""CREATE TABLE IF NOT EXISTS portfolio_settings(
   user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
   public_token TEXT NOT NULL UNIQUE,
   is_public INTEGER NOT NULL DEFAULT 0,
   show_bio INTEGER NOT NULL DEFAULT 0,
   show_skills INTEGER NOT NULL DEFAULT 1,
   show_projects INTEGER NOT NULL DEFAULT 1,
   show_certificates INTEGER NOT NULL DEFAULT 0,
   show_achievements INTEGER NOT NULL DEFAULT 0,
   github_url TEXT NOT NULL DEFAULT '',
   linkedin_url TEXT NOT NULL DEFAULT ''
  )""")

  job_cols={r['name'] for r in c.execute('PRAGMA table_info(jobs)')}
  if 'owner_id' not in job_cols:c.execute('ALTER TABLE jobs ADD COLUMN owner_id INTEGER REFERENCES users(id)')
  if 'location' not in job_cols:c.execute("ALTER TABLE jobs ADD COLUMN location TEXT NOT NULL DEFAULT ''")
  if 'contact_url' not in job_cols:c.execute("ALTER TABLE jobs ADD COLUMN contact_url TEXT NOT NULL DEFAULT ''")
  if 'status' not in job_cols:c.execute("ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'published'")
  columns={r['name'] for r in c.execute('PRAGMA table_info(posts)')}
  if 'topic' not in columns:c.execute("ALTER TABLE posts ADD COLUMN topic TEXT NOT NULL DEFAULT 'Geral'")
  if 'kind' not in columns:c.execute("ALTER TABLE posts ADD COLUMN kind TEXT NOT NULL DEFAULT 'discussao'")
  if 'hidden' not in columns:c.execute('ALTER TABLE posts ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0')
  if 'salary' not in job_cols:c.execute("ALTER TABLE jobs ADD COLUMN salary TEXT NOT NULL DEFAULT ''")
  app_cols={r['name'] for r in c.execute('PRAGMA table_info(job_applications)')}
  if 'status' not in app_cols:c.execute("ALTER TABLE job_applications ADD COLUMN status TEXT NOT NULL DEFAULT 'Enviada'")
  comment_cols={r['name'] for r in c.execute('PRAGMA table_info(community_comments)')}
  if 'parent_id' not in comment_cols:c.execute('ALTER TABLE community_comments ADD COLUMN parent_id INTEGER REFERENCES community_comments(id) ON DELETE SET NULL')
  # Sem vagas fictícias: a lista começa vazia até uma publicação real.

init_db()

def auth_schema():
 with db() as c:
  cols={r['name'] for r in c.execute('PRAGMA table_info(users)')}
  if 'email_verified' not in cols:c.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0')
  c.executescript("""CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS email_verification_tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS auth_mail_limits(kind TEXT NOT NULL,email_hash TEXT NOT NULL,sent_at TEXT NOT NULL,PRIMARY KEY(kind,email_hash));""")
auth_schema()
_original_init_db=init_db
def init_db():
 _original_init_db();auth_schema()

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

def end_session():
 sid=session.get('sid')
 if sid:
  with db() as c:c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(token_hash(sid),))
 session.clear()

def begin_session(uid):
 end_session();sid=secrets.token_urlsafe(32)
 with db() as c:
  c.execute('DELETE FROM auth_sessions WHERE expires_at<=?',(datetime.now(timezone.utc).isoformat(),))
  c.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(token_hash(sid),uid,(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()))
 session.permanent=True;session['uid']=uid;session['sid']=sid

@app.before_request
def validate_session():
 if session.get('uid'):
  sid=session.get('sid')
  with db() as c:
   valid=sid and c.execute('SELECT 1 FROM auth_sessions WHERE token_hash=? AND user_id=? AND expires_at>?',(token_hash(sid),session['uid'],datetime.now(timezone.utc).isoformat())).fetchone()
  if not valid:session.clear()

@app.after_request
def auth_cache(response):
 if request.path.startswith(('/auth/','/data/')) or request.path=='/entrar':response.headers['Cache-Control']='no-store'
 if request.path=='/entrar':response.headers['Referrer-Policy']='no-referrer'
 return response

def persist_catalog_course(c, course):
 """Sincroniza metadados e aulas do curso numa única transação SQLite."""
 cid=course['id']
 c.execute('INSERT INTO catalog_courses(course_id,payload) VALUES(?,?) ON CONFLICT(course_id) DO UPDATE SET payload=excluded.payload,updated_at=CURRENT_TIMESTAMP',(cid,json.dumps({k:v for k,v in course.items() if k!='lessons'},ensure_ascii=False)))
 c.execute('DELETE FROM catalog_lessons WHERE course_id=?',(cid,))
 for pos,lesson in enumerate(course.get('lessons',[])):
  c.execute('INSERT INTO catalog_lessons(lesson_id,course_id,position,payload) VALUES(?,?,?,?)',(lesson['id'],cid,pos,json.dumps(lesson,ensure_ascii=False)))

def load_admin_courses():
 """SQLite é a fonte de verdade; curriculo.json apenas semeia instalações novas."""
 with db() as c:
  for course in CURRICULUM['courses']:
   if not c.execute('SELECT 1 FROM catalog_courses WHERE course_id=?',(course['id'],)).fetchone():persist_catalog_course(c,course)
  # Migração de personalizações legadas; preserva o catálogo já personalizado.
  for row in c.execute('SELECT course_id,payload FROM admin_course_data').fetchall():
   try:
    custom=json.loads(row['payload'])
    if custom.get('id')!=row['course_id'] or not isinstance(custom.get('lessons'),list):continue
    persist_catalog_course(c,custom)
   except (ValueError,KeyError,sqlite3.IntegrityError):continue
  assessments.upgrade_legacy_questions(c)
  catalog={}
  for row in c.execute('SELECT course_id,payload FROM catalog_courses'):
   try:
    course=json.loads(row['payload']);course['lessons']=[];catalog[row['course_id']]=course
   except (ValueError,TypeError):continue
  for row in c.execute('SELECT course_id,payload FROM catalog_lessons ORDER BY course_id,position'):
   if row['course_id'] in catalog:
    try:catalog[row['course_id']]['lessons'].append(json.loads(row['payload']))
    except (ValueError,TypeError):continue
 COURSES.clear();COURSES.update(catalog)
 LESSONS.clear();LESSONS.update({l['id']:(c,l) for c in COURSES.values() for l in c['lessons']})

load_admin_courses()
from codestart_engine import bp
app.register_blueprint(bp)

def auth_required(fn):
 @wraps(fn)
 def wrap(*a,**kw):
  if not session.get('uid'):return jsonify(error='Faça login para continuar.'),401
  return fn(*a,**kw)
 return wrap

def data():return request.get_json(silent=True) or {}
def error(s,code=400):return jsonify(error=s),code

def user():
 if not session.get('uid'):return None
 with db() as c:r=c.execute('SELECT id,name,email,account_type,company_name,bio,goal,level,interests,occupation,languages,avatar_url,email_verified FROM users WHERE id=?',(session['uid'],)).fetchone()
 return dict(r) if r else None

PAGES={'/mensagens':'professionalchat','/business/candidaturas':'candidates','/business/entrevistas':'interviews','/business/relatorios':'reports','/':'dashboard','/dashboard':'dashboard','/cursos':'courses','/desafios':'challenges','/perfil':'profile','/certificados':'certificates','/oportunidades':'jobs','/portfolio':'profile','/comunidade':'community','/laboratorio':'lab','/tutora':'tutor','/lia':'tutor','/entrar':'auth','/projetos':'projects','/trilha-personalizada':'planner','/administracao':'admin'}
for path,pg in PAGES.items():
 def view(pg=pg):
  if pg=='admin':
   if not session.get('uid'):return render_template('page.html',page='auth'),401
   with db() as d:
    if not d.execute('SELECT 1 FROM admins WHERE user_id=?',(session['uid'],)).fetchone():return 'Acesso administrativo não autorizado',403
  response=app.make_response(render_template('page.html',page=pg))
  response.headers['Cache-Control']='no-store'
  return response
 app.add_url_rule(path,endpoint='page_'+pg+'_'+path.replace('/','_'),view_func=view)
@app.get('/curso/<cid>')
def course_page(cid):
 if cid not in COURSES:return 'Curso não encontrado',404
 with db() as c:c.execute('INSERT INTO course_views(user_id,course_id) VALUES(?,?)',(session.get('uid'),cid))
 return render_template('page.html',page='course',course_id=cid)
@app.get('/certificado/verificar/<code>')
def verify_page(code):return render_template('page.html',page='verify',verify_code=code)

@app.post('/auth/register')
def register():
 x=data();name=str(x.get('name','')).strip();email=str(x.get('email','')).strip().lower();pw=str(x.get('password',''))
 if len(name)<2 or len(name)>90 or not valid_email(email) or not 8<=len(pw)<=128:return error('Informe nome, e-mail válido e senha com pelo menos 8 caracteres.')
 account_type=str(x.get('account_type','student'))
 if account_type not in ('student','employer','company'):return error('Tipo de conta inválido.')
 company=str(x.get('company_name','')).strip()
 profile={}
 for field,limit in [('goal',180),('level',40),('interests',300),('occupation',120),('languages',250)]:
  value=x.get(field,'')
  if not isinstance(value,str):return error('Dados do perfil inválidos.')
  profile[field]=value.strip()[:limit]
 if profile['level'] and profile['level'] not in ('iniciante','intermediario','avancado'):return error('Nível de programação inválido.')
 if account_type in ('employer','company') and not 2<=len(company)<=120:return error('Informe o nome da empresa ou organização.')
 try:
  with db() as c:
   r=c.execute('INSERT INTO users(name,email,password,account_type,company_name,goal,level,interests,occupation,languages) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,email,generate_password_hash(pw),account_type,company if account_type in ('employer','company') else '',profile['goal'],profile['level'],profile['interests'],profile['occupation'],profile['languages']));uid=r.lastrowid
 except sqlite3.IntegrityError:return error('E-mail já cadastrado.')
 begin_session(uid)
 verification_sent=False
 if mail_ready():
  try: issue_verification(uid,email);verification_sent=True
  except Exception:app.logger.warning('Falha no envio de confirmação de e-mail')
 return jsonify(ok=True,verification_sent=verification_sent,redirect='/perfil#configuracoes')
@app.post('/auth/login')
def login():
 x=data()
 with db() as c:r=c.execute('SELECT * FROM users WHERE email=?',(str(x.get('email','')).strip().lower(),)).fetchone()
 if not r or not check_password_hash(r['password'],str(x.get('password',''))):return error('E-mail ou senha incorretos.',401)
 begin_session(r['id'])
 with db() as c:is_admin=bool(c.execute('SELECT 1 FROM admins WHERE user_id=?',(r['id'],)).fetchone())
 return jsonify(ok=True,redirect='/administracao' if is_admin else '/oportunidades' if r['account_type']=='employer' else '/dashboard')
def valid_email(email):
 return len(email)<=254 and bool(re.fullmatch(r'[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+',email))

def mail_ready():
 return bool(os.getenv('RESEND_API_KEY') and os.getenv('MAIL_FROM') and os.getenv('PUBLIC_BASE_URL'))

def send_auth_email(email,subject,text):
 payload=json.dumps({'from':os.environ['MAIL_FROM'],'to':[email],'subject':subject,'text':text}).encode()
 req=urllib.request.Request('https://api.resend.com/emails',data=payload,headers={'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],'Content-Type':'application/json','User-Agent':'ConectaElas/1.0'},method='POST')
 with urllib.request.urlopen(req,timeout=15) as response:
  if not 200<=response.status<300:raise OSError('Falha no serviço de e-mail')

def mail_limit(kind,email):
 now=datetime.now(timezone.utc);digest=token_hash(email)
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('SELECT sent_at FROM auth_mail_limits WHERE kind=? AND email_hash=?',(kind,digest)).fetchone()
  if row and datetime.fromisoformat(row['sent_at'])>now-timedelta(minutes=2):return False
  c.execute('INSERT OR REPLACE INTO auth_mail_limits VALUES(?,?,?)',(kind,digest,now.isoformat()))
 return True

def issue_verification(uid,email):
 if not mail_limit('verify',email):return
 token=secrets.token_urlsafe(32)
 with db() as c:
  c.execute('DELETE FROM email_verification_tokens WHERE user_id=?',(uid,))
  c.execute('INSERT INTO email_verification_tokens VALUES(?,?,?)',(token_hash(token),uid,(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()))
 send_auth_email(email,'ConectaElas — confirme seu e-mail','Confirme seu endereço de e-mail: '+os.environ['PUBLIC_BASE_URL'].rstrip('/')+'/entrar?verify_token='+token+'\nVálido por 24 horas. Ignore se não solicitou.')

@app.post('/auth/email/resend')
@auth_required
def resend_verification():
 if not mail_ready():return error('O envio de e-mails ainda não foi configurado.',503)
 u=user()
 if u['email_verified']:return jsonify(ok=True,message='Seu e-mail já está confirmado.')
 try:issue_verification(u['id'],u['email'])
 except Exception:return error('Não foi possível enviar agora. Tente novamente mais tarde.',503)
 return jsonify(ok=True,message='Confira sua caixa de entrada e spam. Aguarde dois minutos antes de reenviar.')

@app.post('/auth/email/verify')
def verify_email():
 token=str(data().get('token',''))
 if not 20<=len(token)<=256:return error('Link inválido ou expirado.')
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('SELECT user_id FROM email_verification_tokens WHERE token_hash=? AND expires_at>?',(token_hash(token),datetime.now(timezone.utc).isoformat())).fetchone()
  if not row:return error('Link inválido ou expirado.')
  c.execute('UPDATE users SET email_verified=1 WHERE id=?',(row['user_id'],))
  c.execute('DELETE FROM email_verification_tokens WHERE user_id=?',(row['user_id'],))
 return jsonify(ok=True,message='E-mail confirmado com sucesso!')

@app.post('/auth/password/forgot')
def forgot_password():
 email=str(data().get('email','')).strip().lower()
 if not valid_email(email):return error('Informe um endereço de e-mail válido.')
 if not mail_ready():return error('A recuperação por e-mail ainda não foi configurada pela administração.',503)
 generic=jsonify(ok=True,message='Se houver uma conta correspondente, enviaremos um link. Confira a caixa de entrada e spam.')
 if not mail_limit('reset',email):return generic
 with db() as d:
  row=d.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
  if not row:return generic
  token=secrets.token_urlsafe(32);digest=token_hash(token)
  expiry=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()
  d.execute('DELETE FROM password_reset_tokens WHERE user_id=?',(row['id'],))
  d.execute('INSERT INTO password_reset_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)',(digest,row['id'],expiry))
 try:send_auth_email(email,'ConectaElas — redefinir senha','Redefina sua senha em '+os.environ['PUBLIC_BASE_URL'].rstrip('/')+'/entrar?reset_token='+token+'\nVálido por 30 minutos. Ignore se não solicitou.')
 except Exception:app.logger.warning('Falha no serviço de recuperação de senha')
 return generic

@app.post('/auth/password/reset')
def reset_password():
 x=data();token=str(x.get('token',''));password=str(x.get('password',''))
 if not 12<=len(password)<=128 or len(token)>256:return error('Informe uma senha de 12 a 128 caracteres e um token válido.')
 digest=hashlib.sha256(token.encode()).hexdigest()
 with db() as d:
  d.execute('BEGIN IMMEDIATE')
  row=d.execute('SELECT user_id,expires_at,used_at FROM password_reset_tokens WHERE token_hash=?',(digest,)).fetchone()
  if not row or row['used_at'] or datetime.fromisoformat(row['expires_at'])<=datetime.now(timezone.utc):return error('Link inválido ou expirado.',400)
  d.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),row['user_id']))
  d.execute('UPDATE password_reset_tokens SET used_at=? WHERE token_hash=?',(datetime.now(timezone.utc).isoformat(),digest))
  d.execute('DELETE FROM auth_sessions WHERE user_id=?',(row['user_id'],))
  d.execute('UPDATE users SET email_verified=1 WHERE id=?',(row['user_id'],))
 session.clear()
 return jsonify(ok=True)

@app.post('/auth/logout')
def logout():
 end_session()
 response=jsonify(ok=True,redirect='/entrar?switch=1') if request.is_json else redirect('/entrar?switch=1',303)
 response.headers['Cache-Control']='no-store'
 response.delete_cookie(app.config['SESSION_COOKIE_NAME'],path=app.config['SESSION_COOKIE_PATH'] or '/',domain=app.config['SESSION_COOKIE_DOMAIN'],secure=app.config['SESSION_COOKIE_SECURE'],httponly=True,samesite=app.config['SESSION_COOKIE_SAMESITE'])
 return response
@app.get('/data/me')
def me():
 response=jsonify(user=user());response.headers['Cache-Control']='no-store';return response
@app.post('/data/profile')
@auth_required
def profile_update():
 name=str(data().get('name','')).strip()
 if not 2<=len(name)<=90:return error('Nome deve ter de 2 a 90 caracteres.')
 with db() as c:c.execute('UPDATE users SET name=? WHERE id=?',(name,session['uid']))
 return jsonify(ok=True)
@app.post('/data/profile/details')
@auth_required
def profile_details():
 x=data();fields=('bio','goal','level','interests','occupation','languages','avatar_url')
 vals=[str(x.get(k,'')).strip() for k in fields]
 if 'avatar_url' not in x:vals[-1]=str((user() or {}).get('avatar_url') or '')
 if any(len(v)>500 for v in vals):return error('Cada campo deve ter no máximo 500 caracteres.')
 if vals[-1] and not (vals[-1].startswith('https://') or (vals[-1].startswith('/static/profile_photos/') and '..' not in vals[-1])):return error('A imagem deve usar HTTPS ou uma foto enviada.')
 with db() as c:c.execute('UPDATE users SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?',(*vals,session['uid']))
 return jsonify(ok=True)

@app.post('/data/profile/avatar')
@auth_required
def profile_avatar_upload():
 file=request.files.get('photo')
 if not file:return error('Selecione uma foto.')
 if file.mimetype not in ('image/jpeg','image/png','image/webp'):
  return error('Use JPG, PNG ou WebP.')
 try:
  file.stream.seek(0)
  photo=Image.open(file.stream)
  photo.verify()
  file.stream.seek(0)
  photo=Image.open(file.stream)
  if photo.width*photo.height>12000000:return error('Imagem grande demais.')
  photo.thumbnail((512,512))
  photo=photo.convert('RGB')
  folder=ROOT/'static'/'profile_photos'
  folder.mkdir(parents=True,exist_ok=True)
  name=secrets.token_hex(16)+'.jpg'
  photo.save(folder/name,'JPEG',quality=84,optimize=True)
 except (OSError,ValueError,UnidentifiedImageError,Image.DecompressionBombError):
  return error('Arquivo de imagem inválido.')
 url='/static/profile_photos/'+name
 with db() as c:
  old=c.execute('SELECT avatar_url FROM users WHERE id=?',(session['uid'],)).fetchone()['avatar_url']
  c.execute('UPDATE users SET avatar_url=? WHERE id=?',(url,session['uid']))
 if old and old.startswith('/static/profile_photos/'):
  (ROOT/'static'/'profile_photos'/Path(old).name).unlink(missing_ok=True)
 return jsonify(ok=True,avatar_url=url)

@app.route('/data/profile/notifications',methods=['GET','POST'])
@auth_required
def profile_notifications():
 uid=session['uid']
 if request.method=='POST':
  x=data()
  with db() as c:
   c.execute("""INSERT INTO profile_notifications(user_id,community,courses,opportunities)
    VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
    community=excluded.community,courses=excluded.courses,opportunities=excluded.opportunities""",
    (uid,*[int(x.get(k) is True) for k in ('community','courses','opportunities')]))
 with db() as c:
  r=c.execute('SELECT community,courses,opportunities FROM profile_notifications WHERE user_id=?',(uid,)).fetchone()
 return jsonify(dict(r) if r else {'community':1,'courses':1,'opportunities':1})

@app.post('/data/profile/password')
@auth_required
def profile_password():
 x=data();old=str(x.get('current_password',''));new=str(x.get('new_password',''))
 if len(new)<8:return error('A nova senha deve ter ao menos 8 caracteres.')
 with db() as c:
  r=c.execute('SELECT password FROM users WHERE id=?',(session['uid'],)).fetchone()
  if not r or not check_password_hash(r['password'],old):return error('Senha atual incorreta.',403)
  c.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(new),session['uid']))
 return jsonify(ok=True)

@app.get('/data/profile/preferences')
@auth_required
def get_preferences():
 with db() as c:r=c.execute('SELECT accessibility FROM user_preferences WHERE user_id=?',(session['uid'],)).fetchone()
 return jsonify(accessibility=json.loads(r['accessibility']) if r else {})

@app.post('/data/profile/preferences')
@auth_required
def set_preferences():
 x=data().get('accessibility',{})
 if not isinstance(x,dict) or len(json.dumps(x))>2000:return error('Preferências inválidas.')
 with db() as c:c.execute('INSERT INTO user_preferences(user_id,accessibility) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET accessibility=excluded.accessibility,updated_at=CURRENT_TIMESTAMP',(session['uid'],json.dumps(x)))
 return jsonify(ok=True)

@app.post('/data/community/block/<int:uid>')
@auth_required
def block_user(uid):
 if uid==session['uid']:return error('Não é possível bloquear sua própria conta.')
 with db() as c:
  if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():return error('Usuária não encontrada.',404)
  c.execute('INSERT OR IGNORE INTO community_blocks(user_id,blocked_user_id) VALUES(?,?)',(session['uid'],uid))
  c.execute("UPDATE community_requests SET status='declined' WHERE status='pending' AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?))",(session['uid'],uid,uid,session['uid']))
 return jsonify(ok=True)

@app.delete('/data/community/block/<int:uid>')
@auth_required
def unblock_user(uid):
 with db() as c:c.execute('DELETE FROM community_blocks WHERE user_id=? AND blocked_user_id=?',(session['uid'],uid))
 return jsonify(ok=True)

@app.get('/data/courses')
def courses():
 with db() as c:
  uid=session.get('uid',-1)
  done={r['lesson_id'] for r in c.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))}
  favorites={r['course_id'] for r in c.execute('SELECT course_id FROM course_favorites WHERE user_id=?',(uid,))}
  enrolled={r['course_id'] for r in c.execute('SELECT course_id FROM course_enrollments WHERE user_id=?',(uid,))}
  passed=passed_modules(c,uid)
 result=[]
 for x in COURSES.values():
  total=len(x['lessons']);count=sum(l['id'] in done for l in x['lessons'])
  status='concluido' if course_finished(x,done,passed) else 'andamento' if count or x['id'] in enrolled else 'nao_iniciado'
  result.append(dict(id=x['id'],name=x['name'],description=x['description'],level=x['level'],category=x.get('category','Geral'),hours=x.get('hours',0),favorite=x['id'] in favorites,total=total,done=count,status=status))
 return jsonify(result)

@app.post('/data/courses/<cid>/start')
@auth_required
def start_course(cid):
 if cid not in COURSES:return jsonify(error='Curso não encontrado.'),404
 with db() as c:
  c.execute('INSERT OR IGNORE INTO course_enrollments(user_id,course_id) VALUES(?,?)',(session['uid'],cid))
 return jsonify(ok=True,course_id=cid)

@app.post('/data/courses/<cid>/favorite')
@auth_required
def favorite_course(cid):
 if cid not in COURSES:return error('Curso não encontrado.',404)
 with db() as c:
  row=c.execute('SELECT 1 FROM course_favorites WHERE user_id=? AND course_id=?',(session['uid'],cid)).fetchone()
  if row:c.execute('DELETE FROM course_favorites WHERE user_id=? AND course_id=?',(session['uid'],cid))
  else:c.execute('INSERT INTO course_favorites(user_id,course_id) VALUES(?,?)',(session['uid'],cid))
 return jsonify(favorite=not bool(row))

def module_groups(course):
 groups=[]
 for lesson in course['lessons']:
  name=lesson.get('module','Módulo')
  if not groups or groups[-1][0]!=name:groups.append((name,[]))
  groups[-1][1].append(lesson)
 return groups

def passed_modules(d,uid):
 return {(r['course_id'],r['module']) for r in d.execute('SELECT course_id,module FROM module_assessments WHERE user_id=?',(uid,))}

def course_finished(course,done,passed):
 return bool(course['lessons']) and all(l['id'] in done for l in course['lessons']) and all((course['id'],name) in passed for name,_ in module_groups(course))

def ensure_certificate(d,uid,cid):
 course=COURSES[cid]
 done={r['lesson_id'] for r in d.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))}
 if not course_finished(course,done,passed_modules(d,uid)):return None
 d.execute('INSERT OR IGNORE INTO certificates(user_id,course_id,code) VALUES(?,?,?)',(uid,cid,secrets.token_hex(12).upper()))
 row=d.execute('SELECT c.code FROM certificates c WHERE c.user_id=? AND c.course_id=? AND NOT EXISTS(SELECT 1 FROM certificate_revocations r WHERE r.code=c.code)',(uid,cid)).fetchone()
 return row['code'] if row else None

def access_state(cid,uid):
 course=COURSES[cid];groups=module_groups(course)
 with db() as d:
  done={r['lesson_id'] for r in d.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))}
  passed={r['module'] for r in d.execute('SELECT module FROM module_assessments WHERE user_id=? AND course_id=?',(uid,cid))}
 states={};unlocked=True
 for name,lessons in groups:
  states[name]={'unlocked':unlocked,'passed':name in passed,'done':sum(l['id'] in done for l in lessons),'total':len(lessons)}
  unlocked=unlocked and name in passed
 return states,done

@app.get('/data/course/<cid>/modules')
def course_modules(cid):
 if cid not in COURSES:return error('Curso não encontrado.',404)
 states,_=access_state(cid,session.get('uid',-1))
 return jsonify([{'name':name,**states[name]} for name,_ in module_groups(COURSES[cid])])

def lesson_open(course, lesson, states, done):
 # Todas as aulas exigem a conclusão da anterior; revisões já concluídas são permitidas.
 module=lesson.get('module','Módulo')
 if not states.get(module,{}).get('unlocked'):return False
 if lesson['id'] in done:return True
 lessons=course['lessons']
 pos=next((i for i,l in enumerate(lessons) if l['id']==lesson['id']),-1)
 return pos>=0 and (pos==0 or lessons[pos-1]['id'] in done)

def module_ready(cid,name,uid):
 if cid not in COURSES:return None,error('Curso não encontrado.',404)
 if not isinstance(name,str):return None,error('Informe um módulo válido.')
 groups=dict(module_groups(COURSES[cid]))
 if name not in groups:return None,error('Módulo inválido.')
 states,done=access_state(cid,uid)
 if not states[name]['unlocked']:return None,error('Conclua o módulo anterior primeiro.',403)
 lessons=groups[name]
 if any(l['id'] not in done for l in lessons):return None,error('Conclua todas as aulas deste módulo antes da avaliação.',403)
 return lessons,None

@app.get('/data/course/<cid>/module/assessment')
@auth_required
def module_assessment_data(cid):
 name=request.args.get('module','');uid=session['uid']
 lessons,err=module_ready(cid,name,uid)
 if err:return err
 practice=assessments.practice_for(cid,name,lessons)
 items=assessments.quiz_items(lessons)
 with db() as d:
  delivery=d.execute('SELECT solution,test_notes,updated_at FROM module_practice_submissions WHERE user_id=? AND course_id=? AND module=?',(uid,cid,name)).fetchone()
  previous=d.execute('SELECT score,passed,created_at FROM module_exam_attempts WHERE user_id=? AND course_id=? AND module=? ORDER BY id DESC LIMIT 1',(uid,cid,name)).fetchone()
 return jsonify(module=name,minimum=assessments.PASS_PERCENT,questions=[dict(id=l['id'],title=l['title'],question=l['question'],options=l['options']) for l in items],practice=dict(task=practice['task'],submission=dict(delivery) if delivery else None),last_attempt=dict(previous) if previous else None)

@app.post('/data/course/<cid>/module/practice')
@auth_required
def submit_module_practice(cid):
 x=data()
 if not isinstance(x,dict):return error('Dados inválidos.')
 name=x.get('module');uid=session['uid']
 lessons,err=module_ready(cid,name,uid)
 if err:return err
 try:solution,tests=assessments.validate_delivery(x)
 except ValueError as exc:return error(str(exc))
 with db() as d:
  d.execute('INSERT INTO module_practice_submissions(user_id,course_id,module,solution,test_notes) VALUES(?,?,?,?,?) ON CONFLICT(user_id,course_id,module) DO UPDATE SET solution=excluded.solution,test_notes=excluded.test_notes,updated_at=CURRENT_TIMESTAMP',(uid,cid,name,solution,tests))
 return jsonify(ok=True,message='Atividade prática entregue. O código não foi executado nem aprovado automaticamente. Você pode responder à avaliação quando quiser.')

@app.post('/data/course/<cid>/module/assessment')
@auth_required
def assess_module(cid):
 x=data()
 if not isinstance(x,dict):return error('Dados inválidos.')
 name=x.get('module');uid=session['uid']
 lessons,err=module_ready(cid,name,uid)
 if err:return err
 practice=assessments.practice_for(cid,name,lessons)
 with db() as d:
  if d.execute('SELECT 1 FROM module_assessments WHERE user_id=? AND course_id=? AND module=?',(uid,cid,name)).fetchone():
   code=ensure_certificate(d,uid,cid)
   return jsonify(correct=True,message='Este módulo já está aprovado.',already_passed=True,certificate_code=code)
  try:result=assessments.grade_module(lessons,practice,x.get('answers'),'')
  except ValueError as exc:return error(str(exc))
  for item in result['results']:
   d.execute('INSERT INTO quiz_attempts(user_id,lesson_id,correct) VALUES(?,?,?)',(uid,item['id'],int(item['correct'])))
  d.execute('INSERT INTO module_exam_attempts(user_id,course_id,module,question_count,correct_count,score,applied_correct,passed,applied_answer) VALUES(?,?,?,?,?,?,?,?,?)',(uid,cid,name,result['total'],result['hits'],result['score'],int(result['applied_correct']),int(result['passed']),''))
  code=None
  if result['passed']:
   d.execute('INSERT OR IGNORE INTO module_assessments(user_id,course_id,module) VALUES(?,?,?)',(uid,cid,name))
   code=ensure_certificate(d,uid,cid)
 good=result['passed']
 return jsonify(correct=good,score=result['score'],hits=result['hits'],total=result['total'],applied_correct=result['applied_correct'],has_applied=result['has_applied'],review_topics=[item['title'] for item in result['results'] if not item['correct']],certificate_code=code,message=('Parabéns! Curso concluído e certificado disponível.' if code else 'Avaliação aprovada! Próximo módulo desbloqueado.') if good else 'Ainda não atingiu os critérios. Revise os conteúdos indicados e tente novamente.')


@app.get('/data/course/<cid>')
def course_data(cid):
 if cid not in COURSES:return error('Curso não encontrado.',404)
 c=COURSES[cid]
 with db() as d:done={r['lesson_id'] for r in d.execute('SELECT lesson_id FROM completions WHERE user_id=?',(session.get('uid',-1),))}
 states,_=access_state(cid,session.get('uid',-1))
 finished=bool(states) and all(m['passed'] and m['done']==m['total'] for m in states.values())
 code=None
 if finished and session.get('uid'):
  with db() as d:code=ensure_certificate(d,session['uid'],cid)
 return jsonify(finished=finished,certificate_code=code,id=cid,name=c['name'],description=c['description'],level=c['level'],category=c.get('category','Geral'),hours=c.get('hours',0),finalProject=c.get('finalProject'),modules=[{'name':n,**states[n]} for n,_ in module_groups(c)],lessons=[dict(id=l['id'],title=l['title'],module=l.get('module','Módulo'),completed=l['id'] in done,locked=not lesson_open(c,l,states,done)) for l in c['lessons']])
@app.get('/data/lesson/<lid>')
def lesson_data(lid):
 if lid not in LESSONS:return error('Aula não encontrada.',404)
 c,l=LESSONS[lid];uid=session.get('uid',-1)
 states,done=access_state(c['id'],uid)
 if not lesson_open(c,l,states,done):return error('Conclua a etapa anterior para desbloquear esta aula.',403)
 with db() as d:
  delivery=d.execute('SELECT solution,test_notes,updated_at FROM lesson_practice_submissions WHERE user_id=? AND lesson_id=?',(uid,lid)).fetchone()
 module=l.get('module','Módulo');groups=dict(module_groups(c))
 practice=assessments.practice_for(c['id'],module,groups[module])
 return jsonify(course=c['id'],title=l['title'],module=module,language=l.get('editorLang','python'),body=l.get('body',''),theory=l.get('theory',[]),objectives=l.get('objectives',[]),practice=l.get('practice',''),challenge=l.get('challenge',''),module_task=practice['task'],practice_submission=dict(delivery) if delivery else None,question=l.get('question',''),options=l.get('options',[]),hints=l.get('hints',[]),codeLines=l.get('codeLines',[]),explanation=l.get('quizExplanation','') if lid in done else '')

@app.post('/data/lesson/<lid>/practice')
@auth_required
def submit_lesson_practice(lid):
 if lid not in LESSONS:return error('Aula não encontrada.',404)
 c,l=LESSONS[lid];uid=session['uid'];states,done=access_state(c['id'],uid)
 if not lesson_open(c,l,states,done):return error('Conclua a etapa anterior primeiro.',403)
 try:solution,tests=assessments.validate_delivery(data())
 except ValueError as exc:return error(str(exc))
 with db() as d:
  d.execute('INSERT INTO lesson_practice_submissions(user_id,lesson_id,solution,test_notes) VALUES(?,?,?,?) ON CONFLICT(user_id,lesson_id) DO UPDATE SET solution=excluded.solution,test_notes=excluded.test_notes,updated_at=CURRENT_TIMESTAMP',(uid,lid,solution,tests))
 return jsonify(ok=True,message='Atividade salva no seu perfil. Esta entrega não foi executada nem corrigida automaticamente.')

@app.post('/data/lesson/<lid>/answer')
@auth_required
def answer(lid):
 if lid not in LESSONS:return error('Aula não encontrada.',404)
 c,l=LESSONS[lid];x=data()
 if not isinstance(x,dict):return error('Dados inválidos.')
 choice=x.get('choice');correct=l.get('correct')
 states,done=access_state(c['id'],session['uid'])
 if not lesson_open(c,l,states,done):return error('Conclua a etapa anterior para desbloquear esta aula.',403)
 if type(choice) is not int or not 0<=choice<len(l.get('options',[])):return error('Selecione uma alternativa válida.')
 good=choice==correct
 with db() as d:
  d.execute('INSERT OR IGNORE INTO course_enrollments(user_id,course_id) VALUES(?,?)',(session['uid'],c['id']))
  d.execute('INSERT INTO quiz_attempts(user_id,lesson_id,correct) VALUES(?,?,?)',(session['uid'],lid,int(good)))
  if good:d.execute('INSERT OR IGNORE INTO completions(user_id,lesson_id) VALUES(?,?)',(session['uid'],lid))
 hints=l.get('hints') or []
 return jsonify(correct=good,explanation=l.get('quizExplanation','') if good else (hints[0] if hints else 'Releia a teoria e teste o exemplo da aula.'),message='Aula concluída!' if good else 'Resposta incorreta. Revise o conteúdo e tente novamente.')
# PASSO 3: desafios educacionais associados ao progresso real dos cursos.
def challenge_access(uid, cid, lesson):
    with db() as conn:
        enrolled = conn.execute('SELECT 1 FROM course_enrollments WHERE user_id=? AND course_id=?',(uid,cid)).fetchone()
        done = {r['lesson_id'] for r in conn.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))}
    course = COURSES[cid]
    lessons = course['lessons']
    position = next((i for i,item in enumerate(lessons) if item['id']==lesson['id']),-1)
    states,_ = access_state(cid,uid)
    module_open = states.get(lesson.get('module','Módulo'),{}).get('unlocked',False)
    unlocked = bool((enrolled or any(l['id'] in done for l in lessons)) and position>=0 and (position==0 or lessons[position-1]['id'] in done) and module_open)
    return unlocked, lesson['id'] in done

@app.get('/data/challenges')
@auth_required
def learning_challenges():
    uid=session['uid']
    with db() as conn:
        enrolled={r['course_id'] for r in conn.execute('SELECT course_id FROM course_enrollments WHERE user_id=?',(uid,))}
        done={r['lesson_id'] for r in conn.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))}
        attempts=conn.execute('SELECT lesson_id,COUNT(*) AS attempts,MAX(correct) AS passed FROM learning_challenge_attempts WHERE user_id=? GROUP BY lesson_id',(uid,)).fetchall()
    attempt_map={r['lesson_id']:dict(r) for r in attempts}
    courses=[]
    for course in COURSES.values():
        cid=course['id']; lessons=course['lessons']
        if cid not in enrolled and not any(l['id'] in done for l in lessons):continue
        states,_=access_state(cid,uid)
        items=[]
        for i,lesson in enumerate(lessons):
            if not lesson.get('question') or not lesson.get('options'):continue
            unlocked=bool(states.get(lesson.get('module','Módulo'),{}).get('unlocked',False) and (i==0 or lessons[i-1]['id'] in done))
            progress=i/max(len(lessons),1)
            difficulty='Iniciante' if progress<1/3 else 'Intermediário' if progress<2/3 else 'Avançado'
            a=attempt_map.get(lesson['id'],{})
            items.append(dict(id=lesson['id'],title=lesson['title'],module=lesson.get('module','Módulo'),difficulty=difficulty,unlocked=unlocked,completed=lesson['id'] in done,attempts=a.get('attempts',0),passed=bool(a.get('passed',0))))
        courses.append(dict(id=cid,name=course['name'],level=course.get('level','Iniciante'),challenges=items))
    return jsonify(courses=courses)

@app.get('/data/challenges/<lid>')
@auth_required
def learning_challenge_detail(lid):
    if lid not in LESSONS:return error('Desafio não encontrado.',404)
    course,lesson=LESSONS[lid]
    unlocked,completed=challenge_access(session['uid'],course['id'],lesson)
    if not unlocked:return error('Conclua as aulas anteriores para liberar este desafio.',403)
    with db() as conn:
        attempts=[dict(r) for r in conn.execute('SELECT answer_index,correct,created_at FROM learning_challenge_attempts WHERE user_id=? AND lesson_id=? ORDER BY id DESC LIMIT 20',(session['uid'],lid))]
    return jsonify(id=lid,title=lesson['title'],course=course['name'],question=lesson.get('question',''),options=lesson.get('options',[]),completed=completed,attempts=attempts,explanation=lesson.get('quizExplanation','') if completed else '')

@app.post('/data/challenges/<lid>/attempt')
@auth_required
def learning_challenge_submit(lid):
    if lid not in LESSONS:return error('Desafio não encontrado.',404)
    course,lesson=LESSONS[lid]
    unlocked,_=challenge_access(session['uid'],course['id'],lesson)
    if not unlocked:return error('Desafio bloqueado: conclua as aulas anteriores.',403)
    choice=data().get('choice')
    if type(choice) is not int or not 0<=choice<len(lesson.get('options',[])):return error('Selecione uma resposta válida.')
    correct=choice==lesson.get('correct')
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO course_enrollments(user_id,course_id) VALUES(?,?)',(session['uid'],course['id']))
        conn.execute('INSERT INTO learning_challenge_attempts(user_id,lesson_id,answer_index,correct) VALUES(?,?,?,?)',(session['uid'],lid,choice,int(correct)))
        if correct:
            conn.execute('INSERT OR IGNORE INTO completions(user_id,lesson_id) VALUES(?,?)',(session['uid'],lid))
    return jsonify(correct=correct,explanation=lesson.get('quizExplanation','') if correct else 'Revise o conceito e teste um exemplo antes de responder.',message='Desafio concluído! Progresso salvo.' if correct else 'Resposta registrada. Revise o conteúdo e tente novamente.')

@app.get('/data/plan')
@auth_required
def get_study_plan():
 with db() as d:
  row=d.execute('SELECT * FROM study_plans WHERE user_id=?',(session['uid'],)).fetchone()
 if not row:return jsonify(plan=None)
 return jsonify(plan=plan_details(dict(row)))

def plan_details(row):
 ids=[cid for cid in json.loads(row['course_ids']) if cid in COURSES]
 with db() as d:
  completed={r['lesson_id'] for r in d.execute('SELECT lesson_id FROM completions WHERE user_id=?',(row['user_id'],))}
  difficulties=d.execute('''WITH attempts AS (SELECT lesson_id,correct,created_at,id,0 source FROM quiz_attempts WHERE user_id=? UNION ALL SELECT lesson_id,correct,created_at,id,1 source FROM learning_challenge_attempts WHERE user_id=?), ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY lesson_id ORDER BY created_at DESC,id DESC,source DESC) rn,SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) OVER(PARTITION BY lesson_id) errors FROM attempts) SELECT lesson_id,errors FROM ranked WHERE rn=1 AND correct=0 ORDER BY errors DESC''',(row['user_id'],row['user_id'])).fetchall()
 reviews=[{'id':r['lesson_id'],'title':LESSONS[r['lesson_id']][1]['title'],'course_id':LESSONS[r['lesson_id']][0]['id'],'course_name':LESSONS[r['lesson_id']][0]['name'],'errors':r['errors']} for r in difficulties if r['lesson_id'] in LESSONS and LESSONS[r['lesson_id']][0]['id'] in ids][:10]
 courses=[];remaining=[]
 for cid in ids:
  c=COURSES[cid];ls=c['lessons'];done=sum(l['id'] in completed for l in ls)
  next_lesson=next((l for l in ls if l['id'] not in completed),None)
  courses.append({'id':cid,'name':c['name'],'level':c['level'],'total':len(ls),'done':done,'percent':round(100*done/len(ls)) if ls else 100,'next_lesson':next_lesson['id'] if next_lesson else None,'next_title':next_lesson['title'] if next_lesson else None})
  remaining.extend([{'id':l['id'],'title':l['title'],'course_id':cid,'course_name':c['name'],'module':l.get('module','Módulo')} for l in ls if l['id'] not in completed])
 total=sum(c['total'] for c in courses);done=sum(c['done'] for c in courses)
 hours=row['hours_per_week'];per_week=max(1,hours*60//35);weeks=[]
 # Allocate review time first, without exceeding the weekly time budget.
 queue=[dict(r,review=True,minutes=15) for r in reviews]+[dict(l,review=False,minutes=35) for l in remaining]
 planned=[];chunk=[];used=0
 for task in queue:
  if used+task['minutes']>hours*60 and chunk:
   planned.append({'number':len(planned)+1,'lessons':chunk,'count':len(chunk),'minutes':used});chunk=[];used=0
  chunk.append(task);used+=task['minutes']
 if chunk:planned.append({'number':len(planned)+1,'lessons':chunk,'count':len(chunk),'minutes':used})
 weeks=planned[:8]
 return {'goal':row['goal'],'level':row['level'],'hours_per_week':hours,'courses':courses,'total':total,'done':done,'percent':round(100*done/total) if total else 0,'remaining':len(remaining),'estimated_weeks':len(planned),'lessons_per_week':per_week,'next':remaining[0] if remaining else None,'weeks':weeks,'reviews':reviews,'created_at':row['created_at']}

@app.post('/data/plan')
@auth_required
def save_study_plan():
 x=data();ids=x.get('course_ids',[])
 if not isinstance(ids,list) or not ids or len(ids)>15 or any(not isinstance(i,str) or i not in COURSES for i in ids):return error('Escolha uma trilha válida.')
 ids=list(dict.fromkeys(ids));goal=str(x.get('goal','')).strip()[:100];level=str(x.get('level','iniciante'))[:30]
 try:hours=int(x.get('hours_per_week',5))
 except (ValueError,TypeError):return error('Informe horas válidas.')
 if hours<1 or hours>40:return error('Escolha entre 1 e 40 horas por semana.')
 with db() as d:
  d.execute("""INSERT INTO study_plans(user_id,goal,level,hours_per_week,course_ids) VALUES(?,?,?,?,?)
  ON CONFLICT(user_id) DO UPDATE SET goal=excluded.goal,level=excluded.level,hours_per_week=excluded.hours_per_week,course_ids=excluded.course_ids,updated_at=CURRENT_TIMESTAMP""",(session['uid'],goal,level,hours,json.dumps(ids)))
 return get_study_plan()

@app.delete('/data/plan')
@auth_required
def delete_study_plan():
 with db() as d:d.execute('DELETE FROM study_plans WHERE user_id=?',(session['uid'],))
 return jsonify(ok=True)

@app.get('/data/dashboard')
@auth_required
def dashboard_data():
 uid=session['uid']
 with db() as d:
  profile=d.execute('SELECT name,goal,level,interests,languages FROM users WHERE id=?',(uid,)).fetchone()
  completed=[dict(r) for r in d.execute('SELECT lesson_id,completed_at FROM completions WHERE user_id=? ORDER BY completed_at DESC',(uid,))]
  certs=[dict(r) for r in d.execute('SELECT course_id,issued_at FROM certificates WHERE user_id=? ORDER BY issued_at DESC',(uid,))]
  favorites={r['course_id'] for r in d.execute('SELECT course_id FROM course_favorites WHERE user_id=?',(uid,))}
  enrolled={r['course_id'] for r in d.execute('SELECT course_id FROM course_enrollments WHERE user_id=?',(uid,))}
  passed=passed_modules(d,uid)
 done_ids={r['lesson_id'] for r in completed}
 started=[];finished=[];pending=[];total_lessons=0;completed_lessons=0
 for c in COURSES.values():
  ids={l['id'] for l in c['lessons']};total=len(ids);done=len(ids & done_ids)
  total_lessons+=total;completed_lessons+=done
  item=dict(id=c['id'],name=c['name'],description=c.get('description',''),category=c.get('category','Geral'),level=c.get('level','Iniciante'),hours=c.get('hours',0),total=total,done=done,percent=round(done/total*100) if total else 0)
  if course_finished(c,done_ids,passed):finished.append(item)
  elif done or c['id'] in enrolled:started.append(item)
  else:pending.append(item)
 profile=dict(profile) if profile else {}
 interests=' '.join(str(profile.get(k) or '') for k in ('goal','interests','languages')).lower()
 def score(c):
  return (5 if c['id'] in favorites else 0)+sum(2 for word in (c['name']+' '+c['category']).lower().split() if len(word)>2 and word in interests)+(1 if c['level'].lower()==str(profile.get('level') or '').lower() else 0)
 recommended=sorted(pending,key=lambda c:(-score(c),c['name']))[:3]
 recent=[]
 for r in completed[:5]:
  pair=LESSONS.get(r['lesson_id'])
  if pair:recent.append(dict(type='lesson',title=pair[1]['title'],course=pair[0]['name'],date=r['completed_at']))
 for r in certs[:5]:
  course=COURSES.get(r['course_id'])
  recent.append(dict(type='certificate',title='Certificado conquistado',course=course['name'] if course else r['course_id'],date=r['issued_at']))
 recent.sort(key=lambda x:x['date'] or '',reverse=True)
 return jsonify(name=profile.get('name',''),started_count=len(started)+len(finished),in_progress_count=len(started),finished_count=len(finished),certificates_count=len(certs),progress=round(completed_lessons/total_lessons*100) if total_lessons else 0,completed_lessons=completed_lessons,total_lessons=total_lessons,started=started[:3],finished=finished[:3],recommendations=recommended,recent=recent[:5])

@app.get('/data/stats')
def stats():
 uid=session.get('uid',-1)
 with db() as d:
  completed=[dict(r) for r in d.execute('SELECT lesson_id,completed_at FROM completions WHERE user_id=?',(uid,))]
  attempts=[dict(r) for r in d.execute('SELECT correct,created_at FROM quiz_attempts WHERE user_id=?',(uid,))]
  certificates=d.execute('SELECT COUNT(*) FROM certificates WHERE user_id=?',(uid,)).fetchone()[0]
 per=[dict(id=c['id'],name=c['name'],done=sum(x['lesson_id'] in {l['id'] for l in c['lessons']} for x in completed),total=len(c['lessons'])) for c in COURSES.values()]
 weekly={}
 for x in completed:
  key=x['completed_at'][:10];weekly[key]=weekly.get(key,0)+1
 return jsonify(completed=len(completed),total=len(LESSONS),xp=len(completed)*20+sum(x['correct'] for x in attempts)*5,attempts=len(attempts),accuracy=round(100*sum(x['correct'] for x in attempts)/len(attempts)) if attempts else 0,certificates=certificates,per_course=per,activity=[{'date':k,'count':v} for k,v in sorted(weekly.items())][-14:])
@app.get('/data/performance')
@auth_required
def performance():
 from datetime import date,timedelta
 uid=session['uid'];today=date.today()
 with db() as d:
  lessons=[dict(r) for r in d.execute('SELECT lesson_id,completed_at FROM completions WHERE user_id=?',(uid,))]
  quizzes=[dict(r) for r in d.execute('SELECT correct,created_at FROM quiz_attempts WHERE user_id=?',(uid,))]
  challenges=[dict(r) for r in d.execute('SELECT passed,created_at FROM editor_challenge_attempts WHERE user_id=?',(uid,))]
  certs=[dict(r) for r in d.execute('SELECT course_id,code,issued_at FROM certificates WHERE user_id=? ORDER BY issued_at DESC',(uid,))]
  goal=d.execute('SELECT target FROM weekly_goals WHERE user_id=?',(uid,)).fetchone()
  plan=d.execute('SELECT course_ids FROM study_plans WHERE user_id=?',(uid,)).fetchone()
  passed=passed_modules(d,uid)
  enrolled={r['course_id'] for r in d.execute('SELECT course_id FROM course_enrollments WHERE user_id=?',(uid,))}
 done={x['lesson_id'] for x in lessons}
 initiated=[];finished=[];languages=[]
 for course in COURSES.values():
  ids={x['id'] for x in course['lessons']};n=len(done&ids)
  if n or course['id'] in enrolled:initiated.append(course['id'])
  if course_finished(course,done,passed):finished.append(course['id'])
  if n:languages.append(dict(name=course['name'],done=n,total=len(ids),percent=round(n/len(ids)*100)))
 events=[x['completed_at'][:10] for x in lessons]+[x['created_at'][:10] for x in quizzes]+[x['created_at'][:10] for x in challenges]
 days=set(events)
 streak=0;cursor=today
 if cursor.isoformat() not in days:cursor-=timedelta(days=1)
 while cursor.isoformat() in days:streak+=1;cursor-=timedelta(days=1)
 week_start=today-timedelta(days=today.weekday())
 weekly=[dict(date=(week_start+timedelta(days=i)).isoformat(),count=events.count((week_start+timedelta(days=i)).isoformat())) for i in range(7)]
 months=[]
 for i in range(5,-1,-1):
  year=today.year;month=today.month-i
  while month<=0:month+=12;year-=1
  key=f'{year:04d}-{month:02d}';months.append(dict(month=key,count=sum(x.startswith(key) for x in events)))
 correct=sum(bool(x['correct']) for x in quizzes)+sum(bool(x['passed']) for x in challenges)
 incorrect=len(quizzes)+len(challenges)-correct
 xp=len(lessons)*20+sum(bool(x['correct']) for x in quizzes)*5
 level=xp//200+1
 achievements=[]
 for label,condition in [('Primeira aula',len(lessons)>=1),('10 aulas concluídas',len(lessons)>=10),('Primeiro certificado',bool(certs)),('7 dias seguidos',streak>=7),('1000 XP',xp>=1000)]:
  achievements.append(dict(name=label,unlocked=condition))
 target=goal['target'] if goal else 5
 week_lessons=sum(x['completed_at'][:10]>=week_start.isoformat() for x in lessons)
 return jsonify(courses_started=len(initiated),courses_completed=len(finished),weekly=weekly,monthly=months,languages=languages,correct=correct,incorrect=incorrect,xp=xp,level=level,achievements=achievements,streak=streak,weekly_goal=target,weekly_done=week_lessons,certificates=[dict(name=COURSES[x['course_id']]['name'] if x['course_id'] in COURSES else x['course_id'],code=x['code'],issued_at=x['issued_at']) for x in certs])

@app.post('/data/performance/goal')
@auth_required
def set_weekly_goal():
 try:target=int(data().get('target'))
 except (ValueError,TypeError):return error('Informe uma meta válida.')
 if not 1<=target<=100:return error('A meta deve ser de 1 a 100 aulas por semana.')
 with db() as d:d.execute('INSERT INTO weekly_goals(user_id,target) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET target=excluded.target,updated_at=CURRENT_TIMESTAMP',(session['uid'],target))
 return jsonify(ok=True,target=target)

@app.post('/data/certificate/<cid>')
@auth_required
def issue_certificate(cid):
 if cid not in COURSES:return error('Curso não encontrado.',404)
 with db() as d:code=ensure_certificate(d,session['uid'],cid)
 if not code:return error('Conclua todas as aulas e avaliações do curso. Certificados revogados não podem ser reemitidos automaticamente.')
 return jsonify(ok=True,code=code,url='/certificado/pdf/'+code,verify='/certificado/verificar/'+code)
@app.get('/data/certificates')
@auth_required
def certificates():
 with db() as d:
  uid=session['uid'];done={r['lesson_id'] for r in d.execute('SELECT lesson_id FROM completions WHERE user_id=?',(uid,))};passed=passed_modules(d,uid)
  for cid,course in COURSES.items():
   if course_finished(course,done,passed):ensure_certificate(d,uid,cid)
  rows=[dict(x) for x in d.execute('SELECT c.code,c.course_id,c.issued_at FROM certificates c WHERE c.user_id=? AND NOT EXISTS(SELECT 1 FROM certificate_revocations r WHERE r.code=c.code) ORDER BY c.issued_at DESC',(uid,))]
 for r in rows:
  course=COURSES.get(r['course_id'],{})
  r['course_name']=course.get('name',r['course_id'])
  r['hours']=course.get('hours',0)
 return jsonify(rows)

def certificate_record(code,owner=None):
 if len(code)>64 or not code.isalnum():return None
 with db() as d:
  sql='SELECT c.code,c.course_id,c.issued_at,u.name FROM certificates c JOIN users u ON u.id=c.user_id WHERE c.code=? AND NOT EXISTS (SELECT 1 FROM certificate_revocations cr WHERE cr.code=c.code)'
  params=[code.upper()]
  if owner is not None:sql+=' AND c.user_id=?';params.append(owner)
  return d.execute(sql,params).fetchone()

@app.get('/data/verify/<code>')
def verify(code):
 r=certificate_record(code)
 if not r:return error('Certificado não encontrado.',404)
 course=COURSES.get(r['course_id'],{})
 # Nome, e-mail e dados da conta não são divulgados na consulta pública.
 return jsonify(code=r['code'],course=course.get('name',r['course_id']),hours=course.get('hours',0),issued_at=r['issued_at'][:10],valid=True)

@app.get('/certificado/pdf/<code>')
@auth_required
def pdf_certificate(code):
 r=certificate_record(code,session['uid'])
 if not r:return error('Certificado não encontrado para sua conta.',404)
 course=COURSES.get(r['course_id'],{})
 title=course.get('name',r['course_id'])
 hours=course.get('hours',0)
 date=datetime.strptime(r['issued_at'][:10],'%Y-%m-%d').strftime('%d/%m/%Y')
 verify_url=url_for('verify_page',code=r['code'],_external=True)
 stream=BytesIO()
 from reportlab.pdfgen import canvas
 from reportlab.lib.utils import simpleSplit
 W,H=landscape(A4)
 c=canvas.Canvas(stream,pagesize=(W,H))
 # Editorial design: white paper, restrained purple accents, legible hierarchy.
 purple=colors.HexColor('#532D79');dark=colors.HexColor('#272333');muted=colors.HexColor('#625B6E');light=colors.HexColor('#DDD5E6')
 c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0)
 c.setFillColor(purple);c.rect(0,0,13,H,fill=1,stroke=0)
 c.setFillColor(colors.HexColor('#B99BCB'));c.rect(13,0,3,H,fill=1,stroke=0)
 c.setStrokeColor(light);c.setLineWidth(.8);c.rect(35,30,W-65,H-60,fill=0,stroke=1)
 c.setFillColor(purple);c.setFont('Helvetica-Bold',12);c.drawString(62,H-66,'ConectaElas  |  Educação e Tecnologia')
 c.setFillColor(muted);c.setFont('Helvetica',10);c.drawRightString(W-57,H-66,'FORMAÇÃO EM TECNOLOGIA')
 c.setStrokeColor(light);c.line(62,H-83,W-57,H-83)
 c.setFillColor(purple);c.setFont('Times-Bold',24);c.drawCentredString(W/2,H-128,'Certificado de conclusão')
 c.setFillColor(muted);c.setFont('Helvetica',13);c.drawCentredString(W/2,H-165,'Certificamos que')
 def centered_lines(value,font,size,y,max_width,line_height):
  c.setFont(font,size)
  for line in simpleSplit(str(value),font,size,max_width):
   c.drawCentredString(W/2,y,line);y-=line_height
  return y
 c.setFillColor(dark);y=centered_lines(r['name'],'Times-Bold',32,H-210,W-150,36)
 c.setFillColor(muted);c.setFont('Helvetica',13);c.drawCentredString(W/2,y-3,'concluiu com aproveitamento as aulas e avaliações do curso')
 c.setFillColor(purple);y=centered_lines(title,'Helvetica-Bold',22,y-42,W-150,26)
 c.setFillColor(muted);c.setFont('Helvetica',12);c.drawCentredString(W/2,y-17,f'Carga horária estimada: {hours} horas    •    Conclusão: {date}')
 c.setStrokeColor(light);c.line(62,146,W-57,146)
 c.setFillColor(dark);c.setFont('Helvetica-Bold',11);c.drawString(62,119,'Autenticidade do documento')
 c.setFont('Helvetica',10);c.drawString(62,101,'Código: '+r['code'])
 c.setFillColor(purple);c.setFont('Helvetica',9)
 for i,line in enumerate(simpleSplit(verify_url,'Helvetica',9,W-215)):
  c.drawString(62,84-i*11,line)
 c.linkURL(verify_url,(62,65,W-155,94),relative=0)
 from reportlab.graphics.barcode.qr import QrCodeWidget
 from reportlab.graphics.shapes import Drawing
 from reportlab.graphics import renderPDF
 qr=QrCodeWidget(verify_url);bounds=qr.getBounds();scale=75/(bounds[2]-bounds[0]);drawing=Drawing(75,75,transform=[scale,0,0,scale,0,0]);drawing.add(qr);renderPDF.draw(drawing,c,W-142,64)
 c.setFillColor(muted);c.setFont('Helvetica',8);c.drawCentredString(W/2,43,'Documento de plataforma educacional independente, sem reconhecimento oficial do SENAC ou MEC.')
 c.setTitle('Certificado - '+title);c.save();stream.seek(0)
 return send_file(stream,mimetype='application/pdf',as_attachment=request.args.get('imprimir')!='1',download_name='certificado-conectas-elas-'+r['code']+'.pdf')
@app.get('/oportunidade/<int:jid>')
def job_detail(jid):
 with db() as d:
  if not d.execute('SELECT id FROM jobs WHERE id=?',(jid,)).fetchone():return 'Oportunidade não encontrada',404
 return render_template('page.html',page='jobdetail',job_id=jid)

@app.post('/data/portfolio/<int:pid>/highlight')
@auth_required
def toggle_highlight(pid):
 with db() as d:
  if not d.execute('SELECT 1 FROM portfolio_items WHERE id=? AND user_id=?',(pid,session['uid'])).fetchone():return error('Projeto não encontrado.',404)
  exists=d.execute('SELECT 1 FROM portfolio_highlights WHERE user_id=? AND project_id=?',(session['uid'],pid)).fetchone()
  if exists:d.execute('DELETE FROM portfolio_highlights WHERE user_id=? AND project_id=?',(session['uid'],pid))
  else:d.execute('INSERT INTO portfolio_highlights(user_id,project_id) VALUES(?,?)',(session['uid'],pid))
 return jsonify(highlighted=not bool(exists))

PROJECT_IDEAS=[
 {'id':'pagina-pessoal','title':'Minha página pessoal','level':'Iniciante','language':'HTML','description':'Crie uma apresentação pessoal acessível e responsiva.','objective':'Praticar estrutura HTML, links, imagens e acessibilidade.','starter':'<!doctype html>\n<html lang="pt-BR">\n<head><meta charset="utf-8"><title>Minha página</title></head>\n<body><h1>Olá!</h1></body>\n</html>'},
 {'id':'cartao-css','title':'Cartão de apresentação','level':'Iniciante','language':'CSS','description':'Estilize um cartão de perfil com cores e espaçamentos.','objective':'Praticar seletores, flexbox e responsividade.','starter':'.cartao {\n  padding: 1rem;\n  border-radius: 12px;\n}'},
 {'id':'tarefas-js','title':'Lista de tarefas','level':'Intermediário','language':'JavaScript','description':'Crie uma lista que permita adicionar e concluir tarefas.','objective':'Praticar arrays, funções e manipulação do DOM.','starter':'const tarefas = [];\nfunction adicionar(tarefa) {\n  tarefas.push(tarefa);\n}'},
 {'id':'analise-python','title':'Analisador de notas','level':'Intermediário','language':'Python','description':'Calcule médias e organize resultados de uma turma fictícia.','objective':'Praticar listas, funções e validação de dados.','starter':'def media(notas):\n    return sum(notas) / len(notas) if notas else 0'},
 {'id':'consulta-sql','title':'Relatório de cursos','level':'Intermediário','language':'SQL','description':'Monte consultas para organizar cursos e matrículas fictícias.','objective':'Praticar SELECT, WHERE, JOIN e agregações.','starter':'SELECT * FROM cursos;'},
 {'id':'api-js','title':'API de oportunidades','level':'Avançado','language':'JavaScript','description':'Planeje endpoints para consultar oportunidades profissionais.','objective':'Praticar APIs, validação e tratamento de erros.','starter':'async function listarOportunidades() {\n  return [];\n}'},
 {'id':'painel-python','title':'Painel de progresso','level':'Avançado','language':'Python','description':'Desenvolva a lógica de um painel com estatísticas de aprendizagem.','objective':'Praticar organização de dados, funções e testes.','starter':'def resumo(registros):\n    return {"total": len(registros)}'}
]

@app.get('/data/project-ideas')
def project_ideas():
 return jsonify(ideas=[{k:v for k,v in idea.items() if k!='starter'} for idea in PROJECT_IDEAS])

@app.get('/data/project-ideas/progress')
@auth_required
def project_ideas_progress():
 with db() as d:rows=d.execute("SELECT id,title,language,idea_id,updated_at FROM editor_projects WHERE user_id=? AND idea_id!='' ORDER BY updated_at DESC",(session['uid'],)).fetchall()
 return jsonify(projects=[dict(r) for r in rows])

@app.post('/data/project-ideas/<idea_id>/start')
@auth_required
def project_idea_start(idea_id):
 idea=next((i for i in PROJECT_IDEAS if i['id']==idea_id),None)
 if not idea:return error('Ideia não encontrada.',404)
 with db() as d:
  row=d.execute('SELECT id FROM editor_projects WHERE user_id=? AND idea_id=? ORDER BY id DESC LIMIT 1',(session['uid'],idea_id)).fetchone()
  if row:return jsonify(ok=True,id=row['id'],existing=True)
  pid=d.execute('INSERT INTO editor_projects(user_id,title,language,code,idea_id) VALUES(?,?,?,?,?)',(session['uid'],idea['title'],idea['language'].lower(),idea['starter'],idea_id)).lastrowid
 return jsonify(ok=True,id=pid,existing=False),201

# PASSO 9 — privacidade definida no servidor; nunca confiar só na interface.
PORTFOLIO_FLAGS=('show_bio','show_skills','show_projects','show_certificates','show_achievements')

def portfolio_settings_row(conn, uid):
 row=conn.execute('SELECT * FROM portfolio_settings WHERE user_id=?',(uid,)).fetchone()
 if not row:
  conn.execute('INSERT INTO portfolio_settings(user_id,public_token) VALUES(?,?)',(uid,secrets.token_urlsafe(24)))
  row=conn.execute('SELECT * FROM portfolio_settings WHERE user_id=?',(uid,)).fetchone()
 return dict(row)

@app.get('/data/portfolio/settings')
@auth_required
def portfolio_settings_get():
 with db() as conn: settings=portfolio_settings_row(conn,session['uid'])
 return jsonify(settings)

@app.post('/data/portfolio/settings')
@auth_required
def portfolio_settings_save():
 x=data()
 github=str(x.get('github_url','')).strip()[:300]
 linkedin=str(x.get('linkedin_url','')).strip()[:300]
 if not project_https_url(github) or (github and not github.lower().startswith('https://github.com/')):
  return error('Informe um link HTTPS do GitHub.')
 if not project_https_url(linkedin) or (linkedin and not (linkedin.lower().startswith('https://www.linkedin.com/') or linkedin.lower().startswith('https://linkedin.com/'))):
  return error('Informe um link HTTPS do LinkedIn.')
 flags={k:int(x.get(k) is True) for k in PORTFOLIO_FLAGS}
 is_public=int(x.get('is_public') is True)
 with db() as conn:
  portfolio_settings_row(conn,session['uid'])
  conn.execute('''UPDATE portfolio_settings SET is_public=?,show_bio=?,show_skills=?,show_projects=?,show_certificates=?,show_achievements=?,github_url=?,linkedin_url=? WHERE user_id=?''',
   (is_public,*(flags[k] for k in PORTFOLIO_FLAGS),github,linkedin,session['uid']))
  settings=portfolio_settings_row(conn,session['uid'])
 return jsonify(settings)

@app.post('/data/portfolio/regenerate-link')
@auth_required
def portfolio_regenerate_link():
 with db() as conn:
  portfolio_settings_row(conn,session['uid'])
  conn.execute('UPDATE portfolio_settings SET public_token=? WHERE user_id=?',(secrets.token_urlsafe(24),session['uid']))
  settings=portfolio_settings_row(conn,session['uid'])
 return jsonify(settings)

@app.get('/data/portfolio/public/<token>')
def portfolio_public_data(token):
 if len(token)>128:return error('Portfólio não encontrado.',404)
 with db() as conn:
  settings=conn.execute('SELECT * FROM portfolio_settings WHERE public_token=? AND is_public=1',(token,)).fetchone()
  if not settings:return error('Portfólio não encontrado ou privado.',404)
  settings=dict(settings);uid=settings['user_id']
  person=conn.execute('SELECT name,bio,languages,interests FROM users WHERE id=?',(uid,)).fetchone()
  if not person:return error('Portfólio indisponível.',404)
  result={'name':person['name'],'bio':person['bio'] if settings['show_bio'] else '',
   'skills':person['languages'] if settings['show_skills'] else '',
   'interests':person['interests'] if settings['show_skills'] else '',
   'github_url':settings['github_url'],'linkedin_url':settings['linkedin_url'],
   'projects':[],'certificates':[],'achievements':[]}
  if settings['show_projects']:
   result['projects']=[dict(r) for r in conn.execute('''SELECT p.title,p.description,p.technologies,p.project_url,p.image_url,
    EXISTS(SELECT 1 FROM portfolio_highlights h WHERE h.user_id=p.user_id AND h.project_id=p.id) AS highlighted
    FROM portfolio_items p WHERE p.user_id=? ORDER BY highlighted DESC,p.id DESC''',(uid,))]
  if settings['show_certificates']:
   result['certificates']=[{'course':COURSES.get(r['course_id'],{}).get('name',r['course_id']),
    'code':r['code'],'issued_at':r['issued_at']} for r in conn.execute('''SELECT c.course_id,c.code,c.issued_at FROM certificates c
    WHERE c.user_id=? AND NOT EXISTS(SELECT 1 FROM certificate_revocations r WHERE r.code=c.code) ORDER BY c.issued_at DESC''',(uid,))]
  if settings['show_achievements']:
   result['achievements']=[{'course':COURSES.get(r['course_id'],{}).get('name',r['course_id']),'module':r['module']}
    for r in conn.execute('SELECT course_id,module FROM module_assessments WHERE user_id=? ORDER BY passed_at DESC',(uid,))]
 return jsonify(result)

@app.get('/p/<token>')
def public_portfolio_page(token):
 # Renderizar com a estrutura existente, sem revelar dados na página inicial.
 if len(token)>128:return 'Portfólio não encontrado',404
 return render_template('page.html',page='publicportfolio')

@app.get('/data/portfolio')
@auth_required
def portfolio_list():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT p.*,EXISTS(SELECT 1 FROM portfolio_highlights h WHERE h.project_id=p.id AND h.user_id=p.user_id) AS highlighted FROM portfolio_items p WHERE p.user_id=? ORDER BY highlighted DESC,p.id DESC',(session['uid'],))])

def project_https_url(value, optional=True):
 from urllib.parse import urlsplit
 if not value:return optional
 try:
  parsed=urlsplit(value)
  return parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password and not any(ch.isspace() for ch in value)
 except ValueError:return False

@app.post('/data/portfolio')
@auth_required
def portfolio_create():
 x=data();title=str(x.get('title','')).strip();description=str(x.get('description','')).strip();tech=str(x.get('technologies','')).strip();url=str(x.get('project_url','')).strip();cid=str(x.get('course_id','')).strip();img=str(x.get('image_url','')).strip()
 if not (2<=len(title)<=100 and 10<=len(description)<=1200 and len(tech)<=200 and len(url)<=300 and len(img)<=500):return error('Confira o título, a descrição e os limites dos campos.')
 if not project_https_url(url) or not project_https_url(img):return error('Os links devem usar HTTPS válido.')
 if cid and cid not in COURSES:return error('Curso inválido.')
 with db() as d:
  pid=d.execute('INSERT INTO portfolio_items(user_id,title,description,technologies,project_url,course_id,image_url) VALUES(?,?,?,?,?,?,?)',(session['uid'],title,description,tech,url,cid,img)).lastrowid
 return jsonify(ok=True,id=pid),201

@app.put('/data/portfolio/<int:pid>')
@auth_required
def portfolio_update(pid):
 x=data();title=str(x.get('title','')).strip();description=str(x.get('description','')).strip();tech=str(x.get('technologies','')).strip();url=str(x.get('project_url','')).strip();cid=str(x.get('course_id','')).strip();img=str(x.get('image_url','')).strip()
 if not (2<=len(title)<=100 and 10<=len(description)<=1200 and len(tech)<=200 and len(url)<=300 and len(img)<=500):return error('Confira o título, a descrição e os limites dos campos.')
 if not project_https_url(url) or not project_https_url(img):return error('Os links devem usar HTTPS válido.')
 if cid and cid not in COURSES:return error('Curso inválido.')
 with db() as d:r=d.execute('UPDATE portfolio_items SET title=?,description=?,technologies=?,project_url=?,course_id=?,image_url=? WHERE id=? AND user_id=?',(title,description,tech,url,cid,img,pid,session['uid']))
 if not r.rowcount:return error('Projeto não encontrado.',404)
 return jsonify(ok=True)

@app.delete('/data/portfolio/<int:pid>')
@auth_required
def portfolio_delete(pid):
 with db() as d:r=d.execute('DELETE FROM portfolio_items WHERE id=? AND user_id=?',(pid,session['uid']))
 if not r.rowcount:return error('Projeto não encontrado.',404)
 return jsonify(ok=True)

@app.get('/data/jobs')
def jobs():
 with db() as d:return jsonify([dict(r) | {'location':r['location'] or 'Não informada','area':('Desenvolvimento Web' if 'Front-end' in r['title'] else 'Tecnologia'),'source_type':'empresa' if r['owner_id'] else 'demonstrativa','source_url':r['contact_url'] or None} for r in d.execute("SELECT j.*,CASE WHEN s.job_id IS NULL THEN 0 ELSE 1 END saved, EXISTS(SELECT 1 FROM job_applications a WHERE a.job_id=j.id AND a.user_id=?) applied FROM jobs j LEFT JOIN saved_jobs s ON s.job_id=j.id AND s.user_id=? WHERE j.status='published'",(session.get('uid',-1),session.get('uid',-1)))])
def employer_required(fn):
 @wraps(fn)
 def wrapper(*args,**kwargs):
  if not session.get('uid'):return error('Faça login como contratante.',401)
  with db() as d:
   if not d.execute("SELECT 1 FROM users WHERE id=? AND account_type IN ('employer','company')",(session['uid'],)).fetchone():return error('Apenas contas de contratantes podem publicar vagas.',403)
  return fn(*args,**kwargs)
 return wrapper

@app.get('/data/employer/jobs')
@employer_required
def employer_jobs():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT j.*, (SELECT COUNT(*) FROM job_applications a WHERE a.job_id=j.id) AS application_count FROM jobs j WHERE owner_id=? ORDER BY id DESC',(session['uid'],))])

@app.post('/data/employer/jobs')
@employer_required
def employer_create_job():
 x=data();title=str(x.get('title','')).strip();description=str(x.get('description','')).strip();location=str(x.get('location','')).strip();url=str(x.get('contact_url','')).strip()
 mode=str(x.get('mode','Remoto'));category=str(x.get('category','Estágio'))
 if not 3<=len(title)<=120 or not 20<=len(description)<=3000 or not 2<=len(location)<=120:return error('Informe título, localização e descrição com pelo menos 20 caracteres.')
 if mode not in ('Remoto','Presencial','Híbrido') or category not in ('Estágio','Jovem Aprendiz','Emprego','Freelance','Projeto'):return error('Categoria ou modalidade inválida.')
 if url and (len(url)>500 or not url.startswith('https://')):return error('Use um link HTTPS válido para candidatura.')
 with db() as d:
  company=d.execute('SELECT company_name FROM users WHERE id=?',(session['uid'],)).fetchone()['company_name']
  jid=d.execute('INSERT INTO jobs(title,organization,mode,category,description,owner_id,location,contact_url,salary) VALUES(?,?,?,?,?,?,?,?,?)',(title,company,mode,category,description,session['uid'],location,url,str(x.get('salary','')).strip()[:100])).lastrowid
 return jsonify(ok=True,id=jid),201

@app.put('/data/employer/jobs/<int:jid>')
@employer_required
def employer_edit_job(jid):
 x=data();title=str(x.get('title','')).strip();description=str(x.get('description','')).strip();location=str(x.get('location','')).strip();url=str(x.get('contact_url','')).strip();mode=str(x.get('mode',''));category=str(x.get('category',''))
 if not 3<=len(title)<=120 or not 20<=len(description)<=3000 or not 2<=len(location)<=120 or (url and (len(url)>500 or not url.startswith('https://'))):return error('Confira os campos do anúncio.')
 if mode not in ('Remoto','Presencial','Híbrido') or category not in ('Estágio','Jovem Aprendiz','Emprego','Freelance','Projeto'):return error('Categoria ou modalidade inválida.')
 with db() as d:
  r=d.execute('UPDATE jobs SET title=?,description=?,location=?,contact_url=?,mode=?,category=?,salary=? WHERE id=? AND owner_id=?',(title,description,location,url,mode,category,str(x.get('salary','')).strip()[:100],jid,session['uid']))
  if not r.rowcount:return error('Anúncio não encontrado.',404)
 return jsonify(ok=True)

@app.delete('/data/employer/jobs/<int:jid>')
@employer_required
def employer_delete_job(jid):
 with db() as d:
  r=d.execute('DELETE FROM jobs WHERE id=? AND owner_id=?',(jid,session['uid']))
  if not r.rowcount:return error('Anúncio não encontrado.',404)
 return jsonify(ok=True)

@app.post('/data/jobs/<int:jid>/apply')
@auth_required
def apply_to_job(jid):
 x=data();message=str(x.get('message','')).strip()
 if len(message)>1200:return error('Mensagem muito longa.')
 with db() as d:
  job=d.execute("SELECT owner_id,status FROM jobs WHERE id=?",(jid,)).fetchone()
  if not job or job['status']!='published':return error('Vaga indisponível.',404)
  if job['owner_id'] is None:return error('Vaga demonstrativa: candidaturas não são recebidas.',400)
  if job['owner_id']==session['uid']:return error('Você não pode se candidatar à própria vaga.',400)
  if d.execute('SELECT 1 FROM job_applications WHERE job_id=? AND user_id=?',(jid,session['uid'])).fetchone():return error('Você já se candidatou a esta vaga.',409)
  d.execute('INSERT OR IGNORE INTO job_applications(job_id,user_id,message) VALUES(?,?,?)',(jid,session['uid'],message))
 return jsonify(ok=True),201

@app.get('/data/jobs/applications/mine')
@auth_required
def my_applications():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT a.id,a.job_id,a.created_at,a.status,j.title,j.organization FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE a.user_id=? ORDER BY a.id DESC',(session['uid'],))])

@app.get('/data/employer/applications')
@employer_required
def employer_applications():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT a.id,a.job_id,a.created_at,a.status,a.message,j.title,u.name AS candidate_name FROM job_applications a JOIN jobs j ON j.id=a.job_id JOIN users u ON u.id=a.user_id WHERE j.owner_id=? AND (? IS NULL OR j.id=?) ORDER BY a.id DESC',(session['uid'],request.args.get('job_id',type=int),request.args.get('job_id',type=int)))])

@app.patch('/data/employer/applications/<int:aid>')
@employer_required
def application_status(aid):
 status=data().get('status')
 if status not in ('Enviada','Em análise','Entrevista','Contratada','Encerrada'):return error('Status inválido.')
 with db() as d:
  r=d.execute('UPDATE job_applications SET status=? WHERE id=? AND job_id IN (SELECT id FROM jobs WHERE owner_id=?)',(status,aid,session['uid']))
  if not r.rowcount:return error('Candidatura não encontrada.',404)
 return jsonify(ok=True)

@app.post('/data/jobs/<int:jid>/save')
@auth_required
def save_job(jid):
 with db() as d:
  if not d.execute('SELECT 1 FROM jobs WHERE id=?',(jid,)).fetchone():return error('Vaga não encontrada.',404)
  exists=d.execute('SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?',(session['uid'],jid)).fetchone()
  if exists:d.execute('DELETE FROM saved_jobs WHERE user_id=? AND job_id=?',(session['uid'],jid))
  else:d.execute('INSERT INTO saved_jobs VALUES(?,?)',(session['uid'],jid))
 return jsonify(saved=not bool(exists))
COMMUNITY_TOPICS=('Geral','HTML/CSS','JavaScript','Python','Java','SQL','Flask','React','Git/GitHub','UI/UX','Acessibilidade','APIs','Segurança Web')
COMMUNITY_KINDS=('discussao','projeto','conquista')
def is_moderator(c):
 return bool(session.get('uid') and (c.execute('SELECT 1 FROM community_moderators WHERE user_id=?',(session['uid'],)).fetchone() or c.execute('SELECT 1 FROM admins WHERE user_id=?',(session['uid'],)).fetchone()))
def community_post(c,pid):
 return c.execute('SELECT id FROM posts WHERE id=? AND hidden=0',(pid,)).fetchone()
@app.get('/data/community/meta')
def community_meta():
 with db() as c:return jsonify(topics=COMMUNITY_TOPICS,moderator=is_moderator(c))
@app.get('/data/posts')
@auth_required
def posts():
 topic=request.args.get('topic','Geral')
 if topic not in COMMUNITY_TOPICS:return error('Comunidade inválida.')
 with db() as c:
  rows=c.execute("""SELECT p.id,p.body,p.topic,p.kind,p.created_at,p.user_id,u.name,
  (SELECT count(*) FROM community_likes l WHERE l.post_id=p.id) likes,
  EXISTS(SELECT 1 FROM community_likes l WHERE l.post_id=p.id AND l.user_id=?) liked
  FROM posts p JOIN users u ON u.id=p.user_id WHERE p.hidden=0 AND (?='Geral' OR p.topic=?) AND NOT EXISTS (SELECT 1 FROM community_blocks b WHERE (b.user_id=? AND b.blocked_user_id=p.user_id) OR (b.user_id=p.user_id AND b.blocked_user_id=?)) ORDER BY p.id DESC LIMIT 60""",(session.get('uid',-1),topic,topic,session.get('uid',-1),session.get('uid',-1))).fetchall()
  result=[]
  for row in rows:
   item=dict(row)
   item['comments']=[dict(r) for r in c.execute('SELECT cm.id,cm.parent_id,cm.body,cm.created_at,cm.user_id,u.name FROM community_comments cm JOIN users u ON u.id=cm.user_id WHERE cm.post_id=? AND NOT EXISTS (SELECT 1 FROM community_blocks b WHERE (b.user_id=? AND b.blocked_user_id=cm.user_id) OR (b.user_id=cm.user_id AND b.blocked_user_id=?)) ORDER BY cm.id ASC LIMIT 50',(row['id'],session.get('uid',-1),session.get('uid',-1)))]
   result.append(item)
 return jsonify(result)
@app.post('/data/posts')
@auth_required
def add_post():
 x=data();body=str(x.get('body','')).strip();topic=x.get('topic','Geral');kind=x.get('kind','discussao')
 if not 1<=len(body)<=1000:return error('Publicação precisa ter de 1 a 1000 caracteres.')
 if topic not in COMMUNITY_TOPICS or kind not in COMMUNITY_KINDS:return error('Categoria inválida.')
 with db() as c:c.execute('INSERT INTO posts(user_id,body,topic,kind) VALUES(?,?,?,?)',(session['uid'],body,topic,kind))
 return jsonify(ok=True)
@app.delete('/data/posts/<int:pid>')
@auth_required
def remove_post(pid):
 with db() as c:
  row=c.execute('SELECT user_id FROM posts WHERE id=?',(pid,)).fetchone()
  if not row or (row['user_id']!=session['uid'] and not is_moderator(c)):return error('Sem permissão.',403)
  c.execute('DELETE FROM community_reports WHERE post_id=? OR comment_id IN (SELECT id FROM community_comments WHERE post_id=?)',(pid,pid))
  c.execute('DELETE FROM community_likes WHERE post_id=?',(pid,))
  c.execute('DELETE FROM community_comments WHERE post_id=?',(pid,))
  c.execute('DELETE FROM posts WHERE id=?',(pid,))
 return jsonify(ok=True)
@app.post('/data/posts/<int:pid>/like')
@auth_required
def like_post(pid):
 with db() as c:
  if not community_post(c,pid):return error('Publicação indisponível.',404)
  if c.execute('SELECT 1 FROM posts p JOIN community_blocks b ON (b.user_id=? AND b.blocked_user_id=p.user_id) OR (b.user_id=p.user_id AND b.blocked_user_id=?) WHERE p.id=?',(session['uid'],session['uid'],pid)).fetchone():return error('Interação indisponível.',403)
  old=c.execute('SELECT 1 FROM community_likes WHERE post_id=? AND user_id=?',(pid,session['uid'])).fetchone()
  if old:c.execute('DELETE FROM community_likes WHERE post_id=? AND user_id=?',(pid,session['uid']))
  else:c.execute('INSERT INTO community_likes(post_id,user_id) VALUES(?,?)',(pid,session['uid']))
 return jsonify(liked=not bool(old))
@app.post('/data/posts/<int:pid>/comments')
@auth_required
def add_comment(pid):
 body=str(data().get('body','')).strip()
 if not 1<=len(body)<=500:return error('Comentário precisa ter de 1 a 500 caracteres.')
 with db() as c:
  if not community_post(c,pid):return error('Publicação indisponível.',404)
  if c.execute('SELECT 1 FROM posts p JOIN community_blocks b ON (b.user_id=? AND b.blocked_user_id=p.user_id) OR (b.user_id=p.user_id AND b.blocked_user_id=?) WHERE p.id=?',(session['uid'],session['uid'],pid)).fetchone():return error('Interação indisponível.',403)
  parent=data().get('parent_id')
  if parent is not None:
   if not isinstance(parent,int) or isinstance(parent,bool):return error('Resposta inválida.')
   target=c.execute('SELECT user_id FROM community_comments WHERE id=? AND post_id=?',(parent,pid)).fetchone()
   if not target:return error('Comentário não encontrado.',404)
   if c.execute('SELECT 1 FROM community_blocks WHERE (user_id=? AND blocked_user_id=?) OR (user_id=? AND blocked_user_id=?)',(session['uid'],target['user_id'],target['user_id'],session['uid'])).fetchone():return error('Interação indisponível.',403)
   if target['user_id']!=session['uid']:community_notice(c,target['user_id'],'Uma participante respondeu seu comentário.')
  c.execute('INSERT INTO community_comments(post_id,user_id,body,parent_id) VALUES(?,?,?,?)',(pid,session['uid'],body,parent))
  owner=c.execute('SELECT user_id FROM posts WHERE id=?',(pid,)).fetchone()
  if owner and owner['user_id']!=session['uid']:community_notice(c,owner['user_id'],'Uma participante comentou sua publicação.')
 return jsonify(ok=True)
@app.delete('/data/comments/<int:cid>')
@auth_required
def delete_comment(cid):
 with db() as c:
  row=c.execute('SELECT user_id FROM community_comments WHERE id=?',(cid,)).fetchone()
  if not row or (row['user_id']!=session['uid'] and not is_moderator(c)):return error('Sem permissão.',403)
  c.execute('DELETE FROM community_reports WHERE comment_id=?',(cid,))
  c.execute('DELETE FROM community_comments WHERE id=?',(cid,))
 return jsonify(ok=True)
@app.post('/data/community/report')
@auth_required
def report_content():
 x=data();pid=x.get('post_id');cid=x.get('comment_id');reason=str(x.get('reason','')).strip()
 if bool(pid)==bool(cid) or not 5<=len(reason)<=300:return error('Informe o conteúdo e um motivo de 5 a 300 caracteres.')
 with db() as c:
  if pid and not community_post(c,pid):return error('Publicação indisponível.',404)
  if cid and not c.execute('SELECT 1 FROM community_comments WHERE id=?',(cid,)).fetchone():return error('Comentário indisponível.',404)
  c.execute('INSERT INTO community_reports(post_id,comment_id,reporter_id,reason) VALUES(?,?,?,?)',(pid,cid,session['uid'],reason))
 return jsonify(ok=True)
@app.get('/data/community/moderation')
@auth_required
def moderation_queue():
 with db() as c:
  if not is_moderator(c):return error('Acesso restrito à moderação.',403)
  return jsonify([dict(r) for r in c.execute('SELECT id,post_id,comment_id,reason,status,created_at FROM community_reports WHERE status=? ORDER BY id DESC LIMIT 100',('pending',))])
@app.post('/data/community/moderation/<int:rid>')
@auth_required
def moderate(rid):
 action=data().get('action')
 if action not in ('dismiss','hide'):return error('Ação inválida.')
 with db() as c:
  if not is_moderator(c):return error('Acesso restrito à moderação.',403)
  r=c.execute('SELECT * FROM community_reports WHERE id=? AND status=?',(rid,'pending')).fetchone()
  if not r:return error('Denúncia não encontrada.',404)
  if action=='hide':
   if r['post_id']:c.execute('UPDATE posts SET hidden=1 WHERE id=?',(r['post_id'],))
   if r['comment_id']:c.execute('DELETE FROM community_reports WHERE comment_id=? AND id<>?',(r['comment_id'],rid));c.execute('DELETE FROM community_comments WHERE id=?',(r['comment_id'],))
  c.execute('UPDATE community_reports SET status=? WHERE id=?',('resolved' if action=='hide' else 'dismissed',rid))
 return jsonify(ok=True)


# PASSO 10: perfis voluntários e convites com aceite explícito.
def community_notice(c,uid,message):
 c.execute('INSERT INTO community_notifications(user_id,message) VALUES(?,?)',(uid,message[:200]))
@app.get('/data/community/profile')
@auth_required
def community_own_profile():
 with db() as c:
  row=c.execute('SELECT * FROM community_profiles WHERE user_id=?',(session['uid'],)).fetchone()
 return jsonify(dict(row) if row else {'visible':0,'bio':'','interests':'','skills':'','mentorship':0,'collaboration':0})
@app.post('/data/community/profile')
@auth_required
def community_save_profile():
 x=data();bio=str(x.get('bio','')).strip();interests=str(x.get('interests','')).strip();skills=str(x.get('skills','')).strip()
 if len(bio)>300 or len(interests)>160 or len(skills)>160:return error('Descrição ou interesses muito longos.')
 vals=[int(x.get(k) is True) for k in ('visible','mentorship','collaboration')]
 with db() as c:
  c.execute('''INSERT INTO community_profiles(user_id,visible,bio,interests,skills,mentorship,collaboration)
   VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET visible=excluded.visible,bio=excluded.bio,
   interests=excluded.interests,skills=excluded.skills,mentorship=excluded.mentorship,collaboration=excluded.collaboration''',
   (session['uid'],vals[0],bio,interests,skills,vals[1],vals[2]))
 return jsonify(ok=True)
@app.get('/data/community/people')
@auth_required
def community_people():
 q=request.args.get('q','').strip()[:80].lower()
 with db() as c:
  rows=c.execute('''SELECT u.id,u.name,p.bio,p.interests,p.skills,p.mentorship,p.collaboration
   FROM community_profiles p JOIN users u ON u.id=p.user_id
   WHERE p.visible=1 AND u.id<>? AND NOT EXISTS
   (SELECT 1 FROM community_blocks b WHERE (b.user_id=? AND b.blocked_user_id=u.id)
    OR (b.user_id=u.id AND b.blocked_user_id=?)) ORDER BY u.id DESC LIMIT 80''',
   (session['uid'],session['uid'],session['uid'])).fetchall()
 return jsonify([dict(r) for r in rows if not q or q in (r['name']+' '+r['interests']+' '+r['skills']).lower()][:30])
@app.get('/data/community/blocked')
@auth_required
def community_blocked():
 with db() as c:rows=c.execute('SELECT u.id,u.name FROM community_blocks b JOIN users u ON u.id=b.blocked_user_id WHERE b.user_id=?',(session['uid'],)).fetchall()
 return jsonify([dict(r) for r in rows])
@app.post('/data/community/requests')
@auth_required
def community_request_create():
 x=data();recipient=x.get('recipient_id');kind=x.get('kind');message=str(x.get('message','')).strip()
 if not isinstance(recipient,int) or recipient==session['uid'] or kind not in ('mentoria','colaboracao') or not 10<=len(message)<=300:return error('Confira o convite (10 a 300 caracteres).')
 with db() as c:
  peer=c.execute('SELECT visible,mentorship,collaboration FROM community_profiles WHERE user_id=?',(recipient,)).fetchone()
  if not peer or not peer['visible'] or not peer['mentorship' if kind=='mentoria' else 'collaboration']:return error('Participante indisponível.',404)
  if c.execute('SELECT 1 FROM community_blocks WHERE (user_id=? AND blocked_user_id=?) OR (user_id=? AND blocked_user_id=?)',(session['uid'],recipient,recipient,session['uid'])).fetchone():return error('Convite indisponível.',403)
  if c.execute("SELECT 1 FROM community_requests WHERE sender_id=? AND recipient_id=? AND kind=? AND status='pending'",(session['uid'],recipient,kind)).fetchone():return error('Já existe um convite pendente.')
  c.execute('INSERT INTO community_requests(sender_id,recipient_id,kind,message) VALUES(?,?,?,?)',(session['uid'],recipient,kind,message))
  community_notice(c,recipient,'Você recebeu um convite de '+('mentoria' if kind=='mentoria' else 'colaboração')+'.')
 return jsonify(ok=True)
@app.get('/data/community/requests')
@auth_required
def community_request_list():
 with db() as c:
  rows=c.execute('''SELECT r.id,r.kind,r.message,r.status,r.created_at,r.sender_id,r.recipient_id,
   s.name sender_name,t.name recipient_name FROM community_requests r
   JOIN users s ON s.id=r.sender_id JOIN users t ON t.id=r.recipient_id
   WHERE (r.sender_id=? OR r.recipient_id=?) AND NOT EXISTS
   (SELECT 1 FROM community_blocks b WHERE (b.user_id=r.sender_id AND b.blocked_user_id=r.recipient_id)
   OR (b.user_id=r.recipient_id AND b.blocked_user_id=r.sender_id)) ORDER BY r.id DESC LIMIT 80''',(session['uid'],session['uid'])).fetchall()
 return jsonify([dict(r) for r in rows])
@app.post('/data/community/requests/<int:rid>')
@auth_required
def community_request_answer(rid):
 action=data().get('action')
 if action not in ('accepted','declined','cancelled'):return error('Ação inválida.')
 with db() as c:
  r=c.execute('SELECT * FROM community_requests WHERE id=? AND status=?',(rid,'pending')).fetchone()
  if not r or (action=='cancelled' and r['sender_id']!=session['uid']) or (action!='cancelled' and r['recipient_id']!=session['uid']):return error('Convite indisponível.',403)
  c.execute('UPDATE community_requests SET status=? WHERE id=?',(action,rid))
  community_notice(c,r['sender_id'] if action!='cancelled' else r['recipient_id'],'Um convite de '+('mentoria' if r['kind']=='mentoria' else 'colaboração')+' foi '+{'accepted':'aceito','declined':'recusado','cancelled':'cancelado'}[action]+'.')
 return jsonify(ok=True)
@app.get('/data/community/notifications')
@auth_required
def community_notifications():
 with db() as c:rows=c.execute('SELECT id,message,is_read,created_at FROM community_notifications WHERE user_id=? ORDER BY id DESC LIMIT 50',(session['uid'],)).fetchall()
 return jsonify([dict(r) for r in rows])
@app.post('/data/community/notifications/read')
@auth_required
def community_notifications_read():
 with db() as c:c.execute('UPDATE community_notifications SET is_read=1 WHERE user_id=?',(session['uid'],))
 return jsonify(ok=True)

# ETAPA 4: histórico privado por conta, sem chaves expostas ao navegador.
@app.get('/data/tutor/history')
@auth_required
def tutor_history():
 with db() as c:
  rows=c.execute('SELECT id,role,body,created_at FROM tutor_messages WHERE user_id=? ORDER BY id DESC LIMIT 40',(session['uid'],)).fetchall()
 return jsonify(messages=[dict(r) for r in reversed(rows)])

@app.delete('/data/tutor/history')
@auth_required
def tutor_clear():
 with db() as c:c.execute('DELETE FROM tutor_messages WHERE user_id=?',(session['uid'],))
 return jsonify(ok=True)

@app.post('/data/tutor/message')
@auth_required
def tutor_message():
 payload=data();question=payload.get('question','');level=payload.get('level','iniciante');mode=payload.get('mode','explain');lid=payload.get('lesson_id','')
 if not isinstance(question,str) or not 1<=len(question.strip())<=4000:return error('Escreva uma pergunta de até 4.000 caracteres.')
 if level not in ('iniciante','intermediario','avancado') or mode not in ('explain','debug','lines','hint'):return error('Preferências inválidas.')
 if not isinstance(lid,str):return error('Aula inválida.')
 context=''
 if lid and lid in LESSONS:
  course,lesson=LESSONS[lid];states,_=access_state(course['id'],session['uid'])
  if states[lesson.get('module','Módulo')]['unlocked']:
   context=f"Curso: {course['name']}; módulo: {lesson.get('module','')}; aula: {lesson['title']}; conteúdo: {lesson.get('body','')[:600]}"
 with db() as c:
  rows=c.execute('SELECT role,body FROM tutor_messages WHERE user_id=? ORDER BY id DESC LIMIT 8',(session['uid'],)).fetchall()
 history=[]
 for row in reversed(rows):
  if row['role']=='user':history.append({'q':row['body'][:2000],'text':''})
  elif history:history[-1]['text']=row['body'][:4000]
 history=[h for h in history if h['text']][-4:]
 if not lia_ai.allow(session['uid']):return error('Limite de mensagens atingido.',429)
 messages=[]
 for h in history:messages.extend([{'role':'user','content':h['q']},{'role':'assistant','content':h['text']}])
 messages.append({'role':'user','content':question.strip()})
 answer,err,status=lia_ai.ask_lia(lia_ai.build_system(level,mode,context),messages)
 source='ai'
 if err:
  if os.getenv('LIA_LOCAL_FALLBACK','1')!='1':return error(err,status or 502)
  import lia_local
  answer='Modo educativo local (IA generativa indisponível):\n\n'+lia_local.respond(question.strip(),mode=mode,level=level,context=context)
  source='local-educational'
 with db() as c:
  c.execute('INSERT INTO tutor_messages(user_id,role,body) VALUES(?,?,?)',(session['uid'],'user',question.strip()))
  c.execute('INSERT INTO tutor_messages(user_id,role,body) VALUES(?,?,?)',(session['uid'],'assistant',answer[:12000]))
  c.execute('DELETE FROM tutor_messages WHERE user_id=? AND id NOT IN (SELECT id FROM tutor_messages WHERE user_id=? ORDER BY id DESC LIMIT 100)',(session['uid'],session['uid']))
 return jsonify(answer=answer,mode=source)


EDITOR_LANGUAGES={'javascript','html','css','python','java','json','sql'}
@app.get('/data/editor/projects')
@auth_required
def editor_projects():
 with db() as c: rows=c.execute('SELECT id,title,language,lesson_id,updated_at FROM editor_projects WHERE user_id=? ORDER BY updated_at DESC,id DESC',(session['uid'],)).fetchall()
 return jsonify(projects=[dict(r) for r in rows])

@app.get('/data/editor/projects/<int:pid>')
@auth_required
def editor_project_get(pid):
 with db() as c:r=c.execute('SELECT * FROM editor_projects WHERE id=? AND user_id=?',(pid,session['uid'])).fetchone()
 return jsonify(project=dict(r)) if r else error('Projeto não encontrado.',404)

@app.post('/data/editor/projects')
@auth_required
def editor_project_save():
 x=data();title=str(x.get('title','')).strip();lang=str(x.get('language',''));code=x.get('code','');lid=x.get('lesson_id')
 if not 1<=len(title)<=100 or lang not in EDITOR_LANGUAGES or not isinstance(code,str) or len(code)>50000:return error('Informe título, linguagem e código válido (máximo 50 mil caracteres).')
 if lid is not None and (not isinstance(lid,str) or lid not in LESSONS):return error('Aula inválida.')
 pid=x.get('id')
 with db() as c:
  if pid is not None:
   if not isinstance(pid,int):return error('ID inválido.')
   r=c.execute('UPDATE editor_projects SET title=?,language=?,code=?,lesson_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?',(title,lang,code,lid,pid,session['uid']))
   if not r.rowcount:return error('Projeto não encontrado.',404)
  else:pid=c.execute('INSERT INTO editor_projects(user_id,title,language,code,lesson_id) VALUES(?,?,?,?,?)',(session['uid'],title,lang,code,lid)).lastrowid
 return jsonify(ok=True,id=pid)

@app.delete('/data/editor/projects/<int:pid>')
@auth_required
def editor_project_delete(pid):
 with db() as c:r=c.execute('DELETE FROM editor_projects WHERE id=? AND user_id=?',(pid,session['uid']))
 return jsonify(ok=True) if r.rowcount else error('Projeto não encontrado.',404)

@app.post('/data/editor/challenges/<challenge_id>/attempt')
@auth_required
def editor_challenge_attempt(challenge_id):
 # Resultados de execução no navegador não são confiáveis para premiações ou certificados.
 # Registrar apenas tentativa, sem creditar XP ou progresso com base em dados do cliente.
 if challenge_id not in ('js-soma','js-par','js-saudacao'):return error('Desafio inválido.',404)
 passed=data().get('passed') is True
 with db() as c:c.execute('INSERT INTO editor_challenge_attempts(user_id,challenge_id,passed) VALUES(?,?,?)',(session['uid'],challenge_id,int(passed)))
 return jsonify(ok=True,recorded=True)


# ETAPA 10: permissões persistentes, nunca confiar em papéis enviados pelo navegador.
def admin_required(fn):
 @wraps(fn)
 def wrapper(*args,**kwargs):
  if not session.get('uid'):return error('Entre na sua conta.',401)
  with db() as d:
   if not d.execute('SELECT 1 FROM admins WHERE user_id=?',(session['uid'],)).fetchone():return error('Acesso exclusivo para administradores autorizados.',403)
  return fn(*args,**kwargs)
 return wrapper

def audit(d,action,entity):
 d.execute('INSERT INTO admin_audit(admin_id,action,entity) VALUES(?,?,?)',(session['uid'],action,str(entity)[:120]))

@app.get('/data/admin/access')
@admin_required
def admin_access():return jsonify(ok=True)

@app.get('/data/admin/overview')
@admin_required
def admin_overview():
 with db() as d:
  count=lambda sql:d.execute(sql).fetchone()[0]
  users=count('SELECT COUNT(*) FROM users'); started=count('SELECT COUNT(DISTINCT user_id) FROM completions')
  completed=count('SELECT COUNT(*) FROM certificates')
  views=[dict(r) for r in d.execute('SELECT course_id,COUNT(*) views FROM course_views GROUP BY course_id ORDER BY views DESC LIMIT 10')]
  issues=[dict(r) for r in d.execute('SELECT lesson_id,COUNT(*) errors FROM quiz_attempts WHERE correct=0 GROUP BY lesson_id ORDER BY errors DESC LIMIT 10')]
  return jsonify(users=users,active_students=started,certificates=completed,completion_rate=round(100*completed/max(1,users*len(COURSES)),1),courses=len(COURSES),posts=count('SELECT COUNT(*) FROM posts'),reports=count("SELECT COUNT(*) FROM community_reports WHERE status='pending'"),views=[dict(name=COURSES.get(x['course_id'],{}).get('name',x['course_id']),**x) for x in views],difficulties=issues)

@app.get('/data/admin/courses')
@admin_required
def admin_courses():
 return jsonify([dict(id=c['id'],name=c['name'],description=c.get('description',''),category=c.get('category','Geral'),level=c.get('level','Iniciante'),hours=c.get('hours',0),modules=sorted({l.get('module','Geral') for l in c['lessons']}),lessons=c['lessons']) for c in COURSES.values()])

@app.post('/data/admin/courses')
@admin_required
def admin_save_course():
 x=data();cid=str(x.get('id','')).strip().lower();name=str(x.get('name','')).strip()
 if not cid or len(cid)>60 or not all(ch.isalnum() or ch=='-' for ch in cid) or not 3<=len(name)<=100:return error('ID (letras, números ou hífen) e nome válido são obrigatórios.')
 old=COURSES.get(cid,{});course=dict(old)
 course.update(id=cid,name=name,description=str(x.get('description',''))[:1500],category=str(x.get('category','Geral'))[:80],level=str(x.get('level','Iniciante'))[:50],hours=max(0,min(999,int(x.get('hours',0) or 0))))
 course.setdefault('lessons',[])
 with db() as d:
  d.execute('INSERT INTO admin_course_data(course_id,payload) VALUES(?,?) ON CONFLICT(course_id) DO UPDATE SET payload=excluded.payload,updated_at=CURRENT_TIMESTAMP',(cid,json.dumps(course,ensure_ascii=False)))
  persist_catalog_course(d,course)
  audit(d,'salvar curso',cid)
 COURSES[cid]=course;load_admin_courses()
 return jsonify(ok=True,id=cid)

@app.post('/data/admin/courses/<cid>/lessons')
@admin_required
def admin_save_lesson(cid):
 if cid not in COURSES:return error('Curso não encontrado.',404)
 x=data();lid=str(x.get('id','')).strip();title=str(x.get('title','')).strip();module=str(x.get('module','')).strip()
 if not 3<=len(title)<=120 or not 2<=len(module)<=100:return error('Informe título e módulo válidos.')
 if not lid:lid=cid+'-admin-'+secrets.token_hex(5)
 if lid in LESSONS and LESSONS[lid][0]['id']!=cid:return error('ID de aula já usado por outro curso.')
 course=json.loads(json.dumps(COURSES[cid]));lessons=course['lessons'];existing=next((i for i,l in enumerate(lessons) if l['id']==lid),None)
 lesson=lessons[existing].copy() if existing is not None else {}
 lesson.update(id=lid,title=title,module=module,body=str(x.get('body',''))[:12000],objectives=x.get('objectives',[]) if isinstance(x.get('objectives'),list) else [],theory=x.get('theory',[]) if isinstance(x.get('theory'),list) else [],practice=str(x.get('practice',''))[:5000],challenge=str(x.get('challenge',''))[:5000],question=str(x.get('question',''))[:1500],options=x.get('options',[]) if isinstance(x.get('options'),list) else [],correct=int(x.get('answer',0) or 0),quizExplanation=str(x.get('explanation',''))[:3000])
 if len(lesson['options'])<2 or len(lesson['options'])>6 or not 0<=lesson['correct']<len(lesson['options']):return error('Avaliação: informe de 2 a 6 alternativas e índice correto.')
 if existing is None:lessons.append(lesson)
 else:lessons[existing]=lesson
 with db() as d:
  d.execute('INSERT INTO admin_course_data(course_id,payload) VALUES(?,?) ON CONFLICT(course_id) DO UPDATE SET payload=excluded.payload,updated_at=CURRENT_TIMESTAMP',(cid,json.dumps(course,ensure_ascii=False)))
  persist_catalog_course(d,course)
  audit(d,'salvar aula',lid)
 COURSES[cid]=course;load_admin_courses()
 return jsonify(ok=True,id=lid)

@app.get('/data/admin/jobs')
@admin_required
def admin_jobs():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT * FROM jobs ORDER BY id DESC')])

@app.post('/data/admin/jobs')
@admin_required
def admin_save_job():
 x=data();title=str(x.get('title','')).strip();org=str(x.get('organization','')).strip()
 if not 3<=len(title)<=120 or not 2<=len(org)<=120:return error('Título e organização obrigatórios.')
 with db() as d:
  jid=int(x.get('id') or 0);fields=(title,org,str(x.get('mode','Remoto'))[:50],str(x.get('category','Projeto'))[:50],str(x.get('description',''))[:3000],str(x.get('salary','')).strip()[:100])
  if jid:
   r=d.execute('UPDATE jobs SET title=?,organization=?,mode=?,category=?,description=?,salary=? WHERE id=?',(*fields,jid))
   if not r.rowcount:return error('Oportunidade não encontrada.',404)
  else:jid=d.execute('INSERT INTO jobs(title,organization,mode,category,description,salary) VALUES(?,?,?,?,?,?)',fields).lastrowid
  audit(d,'salvar oportunidade',jid)
 return jsonify(ok=True,id=jid)

@app.get('/data/admin/certificates')
@admin_required
def admin_certificates():
 with db() as d:return jsonify([dict(r) for r in d.execute('SELECT c.code,c.course_id,c.issued_at, u.name,CASE WHEN r.code IS NULL THEN 0 ELSE 1 END revoked FROM certificates c JOIN users u ON u.id=c.user_id LEFT JOIN certificate_revocations r ON r.code=c.code ORDER BY c.id DESC LIMIT 150')])

@app.post('/data/admin/certificates/<code>/revoke')
@admin_required
def admin_revoke_certificate(code):
 reason=str(data().get('reason','')).strip()
 if not 5<=len(reason)<=300:return error('Informe um motivo de 5 a 300 caracteres.')
 with db() as d:
  if not d.execute('SELECT 1 FROM certificates WHERE code=?',(code,)).fetchone():return error('Certificado não encontrado.',404)
  d.execute('INSERT OR REPLACE INTO certificate_revocations(code,reason) VALUES(?,?)',(code,reason));audit(d,'revogar certificado',code)
 return jsonify(ok=True)


# ===== LIA — Laboratório de Inteligência e Aprendizagem (tutora com IA real) =====
import lia_ai

def lia_init():
 with db() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS lia_messages(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,role TEXT NOT NULL CHECK(role IN ('user','assistant')),body TEXT NOT NULL,course_id TEXT NOT NULL DEFAULT '',lesson_id TEXT NOT NULL DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS lia_messages_user_idx ON lia_messages(user_id,id);""")
lia_init()

def lia_lesson_context(lid,uid):
 """Resumo da aula para a LIA. Nunca inclui a alternativa correta (gabarito)."""
 if not lid or lid not in LESSONS:return '',''
 course,lesson=LESSONS[lid]
 try:states,done=access_state(course['id'],uid)
 except KeyError:return '',''
 if not lesson_open(course,lesson,states,done):return '',''
 parts=[f"Curso: {course['name']} (nível {course.get('level','')})",f"Módulo: {lesson.get('module','')}",f"Aula: {lesson['title']}",f"Conteúdo: {lesson.get('body','')[:900]}"]
 if lesson.get('objectives'):parts.append('Objetivos: '+'; '.join(str(x) for x in lesson['objectives'][:4])[:500])
 if lesson.get('practice'):parts.append('Prática proposta: '+str(lesson['practice'])[:400])
 if lesson.get('question'):parts.append('Pergunta de avaliação da aula: '+str(lesson['question'])[:400])
 return '\n'.join(parts),course['id']

@app.get('/data/lia/status')
def lia_status():
 return jsonify(configured=lia_ai.configured(), provider=lia_ai.provider_name(), model=lia_ai.model_name(), **lia_ai.connection_status())

@app.get('/data/lia/history')
@auth_required
def lia_history():
 with db() as c:
  rows=c.execute('SELECT id,role,body,course_id,lesson_id,created_at FROM lia_messages WHERE user_id=? ORDER BY id DESC LIMIT 60',(session['uid'],)).fetchall()
 return jsonify(messages=[dict(r) for r in reversed(rows)],configured=lia_ai.configured(),provider=lia_ai.provider_name(),model=lia_ai.model_name())

@app.delete('/data/lia/history')
@auth_required
def lia_clear():
 with db() as c:c.execute('DELETE FROM lia_messages WHERE user_id=?',(session['uid'],))
 return jsonify(ok=True)

@app.post('/data/lia/chat')
@auth_required
def lia_chat():
 x=data();question=x.get('question','');level=x.get('level','');mode=x.get('mode','explain');lid=x.get('lesson_id','');code=x.get('code','');language=x.get('language','')
 if not isinstance(question,str) or not 1<=len(question.strip())<=4000:return error('Escreva uma pergunta de até 4.000 caracteres.')
 if not level:
  with db() as c:r=c.execute('SELECT level FROM study_plans WHERE user_id=?',(session['uid'],)).fetchone()
  raw=(r['level'] if r else 'iniciante').lower();level='avancado' if raw.startswith('avan') else 'intermediario' if raw.startswith('inter') else 'iniciante'
 if level not in lia_ai.LEVELS or mode not in lia_ai.MODES:return error('Preferências inválidas.')
 if not isinstance(lid,str) or not isinstance(code,str) or not isinstance(language,str) or len(code)>6000:return error('Dados inválidos. O código pode ter até 6.000 caracteres.')
 if not lia_ai.allow(session['uid']):return error('Você enviou muitas mensagens em pouco tempo. Respire um pouco e tente de novo em alguns minutos.',429)
 context,cid=lia_lesson_context(lid,session['uid']);language=language.lower()
 user_text=question.strip()
 if code.strip():user_text+='\n\nCódigo da aluna'+(f' ({language})' if language in lia_ai.LANGUAGES else '')+':\n```\n'+code.strip()+'\n```'
 with db() as c:
  rows=c.execute('SELECT role,body FROM lia_messages WHERE user_id=? ORDER BY id DESC LIMIT 10',(session['uid'],)).fetchall()
 history=[{'role':r['role'],'content':r['body'][:4000]} for r in reversed(rows)]
 while history and history[0]['role']!='user':history.pop(0)
 messages=history+[{'role':'user','content':user_text}]
 system=lia_ai.build_system(level,mode,context,language)
 if user()['account_type']=='company':system+='\nVocê é LIA Business: ajude com comunicação profissional, anúncios inclusivos, entrevistas e indicadores. Não classifique candidatas nem tome decisões de contratação. Não solicite dados pessoais.'
 answer,err,status=lia_ai.ask_lia(system,messages)
 provider=lia_ai.provider_name()
 if err:
  if os.getenv('LIA_LOCAL_FALLBACK','1')!='1':return error(err,status or 502)
  import lia_local
  answer=business_fallback(question) if user()['account_type']=='company' else lia_local.respond(question.strip(),code,language,mode,level,context)
  provider='local-educational'
  answer='Modo educativo local (IA generativa indisponível):\n\n'+answer
 with db() as c:
  c.execute('INSERT INTO lia_messages(user_id,role,body,course_id,lesson_id) VALUES(?,?,?,?,?)',(session['uid'],'user',user_text[:10000],cid,lid if cid else ''))
  c.execute('INSERT INTO lia_messages(user_id,role,body,course_id,lesson_id) VALUES(?,?,?,?,?)',(session['uid'],'assistant',answer[:12000],cid,lid if cid else ''))
  c.execute('DELETE FROM lia_messages WHERE user_id=? AND id NOT IN (SELECT id FROM lia_messages WHERE user_id=? ORDER BY id DESC LIMIT 200)',(session['uid'],session['uid']))
 return jsonify(answer=answer,level=level,lesson=cid,provider=provider)

from business import install_business, business_fallback
install_business(app,db,user,error,data)
from professional_chat import install_chat
install_chat(app,db,auth_required)

if __name__=='__main__':app.run(debug=os.getenv('FLASK_DEBUG')=='1',host='0.0.0.0',port=int(os.getenv('PORT',5000)))
