"""Recruitment communication, limited to professional predefined messages."""
from flask import jsonify, request, session
from contextlib import closing

MESSAGES = {
 'company': {'received':'Recebemos sua candidatura.','review':'Sua candidatura está em análise.','interview':'Você avançou para a etapa de entrevista. Consulte o andamento da candidatura.','result':'O resultado foi atualizado. Consulte suas candidaturas.','welcome':'Boas-vindas à equipe!','training':'Consulte as orientações de integração e treinamento da empresa.'},
 'candidate': {'thanks':'Obrigada pelo retorno.','interest':'Continuo interessada na oportunidade.','confirm':'Confirmo meu interesse na etapa de entrevista.','reschedule':'Preciso solicitar um reagendamento.','status':'Gostaria de receber uma atualização sobre o processo seletivo.','onboarding':'Gostaria de receber orientações sobre a integração.'}
}

def schema(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS professional_messages(id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES job_applications(id) ON DELETE CASCADE, sender_id INTEGER NOT NULL REFERENCES users(id), message_key TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, read_at TEXT);
 CREATE INDEX IF NOT EXISTS professional_messages_application ON professional_messages(application_id,id);
 CREATE TABLE IF NOT EXISTS professional_blocks(application_id INTEGER NOT NULL REFERENCES job_applications(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),PRIMARY KEY(application_id,user_id));
 CREATE TABLE IF NOT EXISTS professional_reports(application_id INTEGER NOT NULL REFERENCES job_applications(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(application_id,user_id));''')

def participant(c, aid, uid):
 return c.execute('SELECT a.id,a.user_id,a.status,j.owner_id,j.title,j.organization FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=? AND j.owner_id IS NOT NULL AND (a.user_id=? OR j.owner_id=?)',(aid,uid,uid)).fetchone()

def install_chat(app,db,auth_required):
 with closing(db()) as c, c: schema(c)
 @app.get('/data/professional-chat')
 @auth_required
 def chat_list():
  uid=session['uid']
  with closing(db()) as c:
   rows=c.execute('''SELECT a.id,a.status,j.title,j.organization,CASE WHEN j.owner_id=? THEN 'company' ELSE 'candidate' END AS role,(SELECT count(*) FROM professional_messages m WHERE m.application_id=a.id AND m.sender_id<>? AND m.read_at IS NULL) AS unread FROM job_applications a JOIN jobs j ON j.id=a.job_id WHERE j.owner_id IS NOT NULL AND (a.user_id=? OR j.owner_id=?) ORDER BY a.id DESC''',(uid,uid,uid,uid))
   return jsonify([dict(r) for r in rows])
 @app.route('/data/professional-chat/<int:aid>',methods=['GET','POST'])
 @auth_required
 def chat_thread(aid):
  uid=session['uid']
  with closing(db()) as c, c:
   a=participant(c,aid,uid)
   if not a:return jsonify(error='Conversa não encontrada.'),404
   role='company' if a['owner_id']==uid else 'candidate'
   blocked=bool(c.execute('SELECT 1 FROM professional_blocks WHERE application_id=?',(aid,)).fetchone())
   closed=a['status']=='Encerrada'
   options={k:v for k,v in MESSAGES[role].items() if k not in ('welcome','training','onboarding') or a['status']=='Contratada'}
   if request.method=='POST':
    if not request.is_json:return jsonify(error='Formato inválido.'),415
    x=request.get_json(silent=True)
    if not isinstance(x,dict):return jsonify(error='Mensagem inválida.'),400
    action=x.get('action','send')
    if action in ('block','report'):
     c.execute('INSERT OR IGNORE INTO professional_blocks(application_id,user_id) VALUES(?,?)',(aid,uid))
     if action=='report':c.execute('INSERT OR IGNORE INTO professional_reports(application_id,user_id) VALUES(?,?)',(aid,uid))
     return jsonify(ok=True)
    key=x.get('key')
    if action!='send' or not isinstance(key,str) or key not in options:return jsonify(error='Selecione uma mensagem profissional disponível.'),400
    if blocked or closed:return jsonify(error='Conversa encerrada ou bloqueada.'),409
    n=c.execute("SELECT count(*) FROM professional_messages WHERE sender_id=? AND created_at>=datetime('now','-1 minute')",(uid,)).fetchone()[0]
    if n>=12:return jsonify(error='Aguarde antes de enviar outra mensagem.'),429
    c.execute('INSERT INTO professional_messages(application_id,sender_id,message_key,body) VALUES(?,?,?,?)',(aid,uid,key,options[key]))
    return jsonify(ok=True),201
   c.execute('UPDATE professional_messages SET read_at=CURRENT_TIMESTAMP WHERE application_id=? AND sender_id<>? AND read_at IS NULL',(aid,uid))
   rows=c.execute('SELECT id,body,created_at,read_at,sender_id=? AS mine FROM professional_messages WHERE application_id=? ORDER BY id DESC LIMIT 200',(uid,aid)).fetchall()
   return jsonify(messages=[dict(r) for r in reversed(rows)],options=options,blocked=blocked,closed=closed,title=a['title'],organization=a['organization'],status=a['status'])
