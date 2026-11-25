from flask import request, jsonify, redirect
from functools import wraps

def business_fallback(question):
 q=question.lower()
 if 'entrevista' in q:return 'Defina competências relevantes, prepare perguntas iguais para todas as candidatas e registre evidências. Use critérios objetivos e ofereça alternativas acessíveis de horário.'
 if 'vaga' in q or 'anúncio' in q:return 'Inclua cargo, responsabilidades, requisitos essenciais, faixa salarial, modalidade, jornada e etapas da seleção. Evite exigências que não sejam necessárias ao cargo.'
 if 'comunica' in q:return 'Informe prazos e próximos passos com clareza. Use linguagem respeitosa e objetiva, mantenha a comunicação dentro do processo seletivo e não solicite dados pessoais desnecessários.'
 return 'Posso orientar sobre anúncios, entrevistas e comunicação empresarial. Qual desses processos você deseja melhorar?'

def install_business(app,db,user,error,data):
 fields={'segment':120,'size':60,'location':120,'website':300,'description':2000,'mission':500,'vision':500,'values':500,'technologies':300,'culture':800,'benefits':800,'training':800}
 with db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS business_profiles(user_id INTEGER PRIMARY KEY REFERENCES users(id), '+','.join('"'+k+'" TEXT NOT NULL DEFAULT '+chr(39)*2 for k in fields)+')')
  c.execute('CREATE TABLE IF NOT EXISTS business_interviews(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id), application_id INTEGER NOT NULL REFERENCES job_applications(id) ON DELETE CASCADE, scheduled TEXT NOT NULL, note TEXT NOT NULL DEFAULT \'\')')
 def company(fn):
  @wraps(fn)
  def wrap(*a,**kw):
   u=user()
   if not u:return error('Entre na conta.',401)
   if u['account_type']!='company':return error('Área exclusiva de empresas.',403)
   return fn(*a,**kw)
  return wrap
 @app.before_request
 def company_guard():
  path=request.path
  if path.startswith('/business/'):
   u=user()
   if not u or u['account_type']!='company':return redirect('/dashboard')
  if not path.startswith(('/data/','/api/','/curso/','/cursos','/desafios','/laboratorio','/projetos','/trilha-personalizada','/certificados','/portfolio','/oportunidade/')):return
  u=user()
  if not u or u['account_type']!='company':return
  if path.startswith(('/data/courses','/data/course/','/data/lesson/','/data/challenges','/data/plan','/data/performance','/data/certificate','/data/editor','/data/project-ideas','/data/portfolio','/data/jobs/applications/mine','/data/profile/details','/data/community/people','/data/community/requests','/api/')) or (path.startswith('/data/jobs/') and path.endswith(('/apply','/save'))):return error('Função reservada a contas individuais.',403)
  if not path.startswith('/data/'):return redirect('/dashboard')
 @app.route('/data/business/profile',methods=['GET','POST'])
 @company
 def business_profile():
  uid=user()['id']
  with db() as c:
   if request.method=='POST':
    x=data(); vals=[str(x.get(k,'' )).strip()[:v] for k,v in fields.items()]
    name=str(x.get('company_name','')).strip()[:120]
    if len(name)<2:return error('Informe o nome empresarial.')
    if vals[3] and not vals[3].startswith('https://'):return error('Use um site HTTPS.')
    c.execute('INSERT INTO business_profiles(user_id,'+','.join('"'+k+'"' for k in fields)+') VALUES('+','.join('?' for _ in range(len(fields)+1))+') ON CONFLICT(user_id) DO UPDATE SET '+','.join('"'+k+'"=excluded."'+k+'"' for k in fields),(uid,*vals))
    c.execute('UPDATE users SET company_name=? WHERE id=?',(name,uid))
   row=c.execute('SELECT * FROM business_profiles WHERE user_id=?',(uid,)).fetchone()
  return jsonify(dict(row) if row else {k:'' for k in fields})
 @app.get('/data/business/overview')
 @company
 def overview():
  uid=user()['id']
  with db() as c:
   jobs=[dict(r) for r in c.execute('SELECT id,title,status FROM jobs WHERE owner_id=?',(uid,))]
   counts={r['status']:r['n'] for r in c.execute('SELECT a.status,count(*) n FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE j.owner_id=? GROUP BY a.status',(uid,))}
   months=[dict(r) for r in c.execute("SELECT substr(a.created_at,1,7) month,count(*) n FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE j.owner_id=? GROUP BY month ORDER BY month DESC LIMIT 6",(uid,))]
  return jsonify(jobs=jobs,counts=counts,months=months[::-1])
 @app.route('/data/business/interviews',methods=['GET','POST'])
 @company
 def interviews():
  uid=user()['id']
  with db() as c:
   if request.method=='POST':
    from datetime import datetime
    x=data(); aid=x.get('application_id'); scheduled=str(x.get('scheduled','')); note=str(x.get('note',''))[:300]
    try:datetime.fromisoformat(scheduled)
    except ValueError:return error('Data inválida.')
    if not c.execute('SELECT 1 FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=? AND j.owner_id=?',(aid,uid)).fetchone():return error('Candidatura não encontrada.',404)
    c.execute('INSERT INTO business_interviews(owner_id,application_id,scheduled,note) VALUES(?,?,?,?)',(uid,aid,scheduled,note))
    c.execute("UPDATE job_applications SET status='Entrevista' WHERE id=?",(aid,))
   rows=c.execute('SELECT i.*,j.title,u.name candidate_name FROM business_interviews i JOIN job_applications a ON a.id=i.application_id JOIN jobs j ON j.id=a.job_id JOIN users u ON u.id=a.user_id WHERE i.owner_id=? ORDER BY scheduled',(uid,)).fetchall()
  return jsonify([dict(r) for r in rows])
