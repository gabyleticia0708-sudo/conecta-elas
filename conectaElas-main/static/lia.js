/* LIA — Laboratório de Inteligência e Aprendizagem (frontend).
   Fala só com o backend Flask (/data/lia/*). A chave da IA nunca chega ao navegador. */
(function () {
  'use strict';
  var d = document;
  var pageName = d.body.dataset.page;
  var LEVELS = [['iniciante', 'Iniciante'], ['intermediario', 'Intermediária'], ['avancado', 'Avançada']];
  var MODES = [['explain', 'Explicar conceito ou código'], ['lines', 'Explicar linha por linha'], ['debug', 'Corrigir erros no meu código'], ['hint', 'Exercício: só pistas']];
  var LANGS = [['python', 'Python'], ['javascript', 'JavaScript'], ['html', 'HTML'], ['css', 'CSS'], ['sql', 'SQL'], ['java', 'Java'], ['json', 'JSON']];
  var SUGGESTIONS = ['O que é uma variável?', 'Como funciona um laço for?', 'Qual a diferença entre lista e dicionário?', 'Me dê uma pista para o exercício de hoje'];

  function el(tag, cls, text) { var e = d.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function lsGet(k, f) { try { return localStorage.getItem(k) || f; } catch (e) { return f; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  async function call(path, method, body) {
    var res = await fetch(path, { method: method || 'GET', headers: { 'Content-Type': 'application/json' }, body: body !== undefined ? JSON.stringify(body) : undefined });
    var x = {};
    try { x = await res.json(); } catch (e) {}
    if (!res.ok) { var err = new Error(x.error || 'Não foi possível falar com a LIA agora.'); err.status = res.status; throw err; }
    return x;
  }
  function isLogged() { return typeof me !== 'undefined' && me; }

  // ---------- Renderização segura das respostas (sem innerHTML com texto da IA) ----------
  function inline(parent, text) {
    text.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).forEach(function (seg) {
      if (!seg) return;
      if (seg.length > 2 && seg[0] === '`') parent.appendChild(el('code', 'lia-inline', seg.slice(1, -1)));
      else if (seg.length > 4 && seg.slice(0, 2) === '**') parent.appendChild(el('strong', '', seg.slice(2, -2)));
      else parent.appendChild(d.createTextNode(seg));
    });
  }
  function renderRich(container, text) {
    container.textContent = '';
    String(text).split('```').forEach(function (part, i) {
      if (i % 2 === 1) {
        var nl = part.indexOf('\n'), lang = '', code = part;
        if (nl >= 0 && /^[a-zA-Z0-9+#-]{0,15}$/.test(part.slice(0, nl).trim())) { lang = part.slice(0, nl).trim(); code = part.slice(nl + 1); }
        var wrap = el('div', 'lia-codewrap');
        var bar = el('div', 'lia-codebar');
        bar.appendChild(el('span', '', lang || 'código'));
        var cp = el('button', 'lia-copy', 'Copiar'); cp.type = 'button';
        cp.setAttribute('aria-label', 'Copiar código' + (lang ? ' ' + lang : ''));
        cp.onclick = function () {
          var ok = function () { cp.textContent = 'Copiado!'; setTimeout(function () { cp.textContent = 'Copiar'; }, 1600); };
          if (navigator.clipboard) navigator.clipboard.writeText(code.replace(/\n$/, '')).then(ok, function () {}); 
        };
        bar.appendChild(cp);
        var pre = el('pre', 'lia-code'); pre.tabIndex = 0; pre.appendChild(el('code', '', code.replace(/\n$/, '')));
        wrap.appendChild(bar); wrap.appendChild(pre); container.appendChild(wrap);
      } else {
        part.split(/\n{2,}/).forEach(function (p) {
          if (!p.trim()) return;
          var para = el('p', 'lia-p'); inline(para, p.trim()); container.appendChild(para);
        });
      }
    });
  }

  function addBubble(log, role, body) {
    var b = el('div', 'lia-bubble ' + (role === 'user' ? 'lia-user' : 'lia-bot'));
    b.appendChild(el('strong', 'lia-who', role === 'user' ? 'Você' : 'LIA'));
    var t = el('div', 'lia-text');
    if (role === 'user') { t.textContent = body; t.style.whiteSpace = 'pre-wrap'; } else renderRich(t, body);
    b.appendChild(t); log.appendChild(b); log.scrollTop = log.scrollHeight; return b;
  }
  function typing(log) {
    var b = el('div', 'lia-bubble lia-bot lia-typing'); b.setAttribute('aria-label', 'A LIA está escrevendo');
    b.appendChild(el('strong', 'lia-who', 'LIA'));
    var dots = el('span', 'lia-dots'); dots.innerHTML = '<i></i><i></i><i></i>'; b.appendChild(dots);
    log.appendChild(b); log.scrollTop = log.scrollHeight; return b;
  }
  function select(id, opts, value, label) {
    var wrap = el('label', 'lia-field'); wrap.appendChild(el('span', '', label));
    var s = el('select', 'field'); s.id = id;
    opts.forEach(function (o) { var op = el('option', '', o[1]); op.value = o[0]; s.appendChild(op); });
    s.value = value; wrap.appendChild(s); return wrap;
  }

  // ---------- Página exclusiva /lia ----------
  async function page() {
    var content = d.getElementById('content');
    var head = (typeof heading === 'function') ? (typeof me!=='undefined'&&me?.account_type==='company'?heading('CONECTAELAS BUSINESS','LIA Business','Assistência para comunicação, recrutamento e inclusão.'):heading('LIA • TUTORA IA', 'LIA — Laboratório de Inteligência e Aprendizagem', 'Sua tutora virtual de programação: explica, corrige e dá pistas no seu ritmo.')) : '<h1>LIA</h1>';
    content.innerHTML = head + '<section class="lia-shell panel" aria-label="Conversa com a LIA"></section>';
    var shell = content.querySelector('.lia-shell');

    if (!isLogged()) {
      shell.innerHTML = '<div class="empty">Entre na sua conta para conversar com a LIA e guardar seu histórico. <a class="link" href="/entrar">Entrar ou cadastrar →</a></div>';
      return;
    }

    var top = el('div', 'lia-top');
    var id = el('div', 'lia-id');
    id.appendChild(el('span', 'lia-avatar', 'L')); id.lastChild.setAttribute('aria-hidden', 'true');
    var idt = el('div'); idt.appendChild(el('strong', '', 'LIA')); var st = el('p', 'small', 'Verificando conexão…'); st.id = 'lia-status'; st.setAttribute('role', 'status'); idt.appendChild(st);
    id.appendChild(idt); top.appendChild(id);
    var clear = el('button', 'btn ghost', 'Limpar conversa'); clear.type = 'button'; top.appendChild(clear); var retry = el('button', 'btn ghost', 'Testar conexão'); retry.type = 'button'; top.appendChild(retry); async function checkConnection(){retry.disabled=true;st.textContent='Verificando servidor Ollama…';try{var r=await call('/data/lia/status');st.textContent=(r.connected?'Ollama acessível • ':'Ollama indisponível • ')+(r.model||'');err.textContent=r.detail||'';}catch(e){st.textContent='Falha ao verificar servidor';err.textContent=e.message;}finally{retry.disabled=false;}} retry.onclick=checkConnection;
    shell.appendChild(top);

    var settings = el('div', 'lia-settings');
    settings.appendChild(select('lia-level', LEVELS, lsGet('ce-lia-level', 'iniciante'), 'Seu nível'));
    settings.appendChild(select('lia-mode', MODES, 'explain', 'Tipo de ajuda'));
    settings.appendChild(select('lia-course', [['', 'Nenhum curso']], '', 'Curso'));
    settings.appendChild(select('lia-lesson', [['', 'Nenhuma aula']], '', 'Aula'));
    shell.appendChild(settings);

    var log = el('div', 'lia-log'); log.setAttribute('role', 'log'); log.setAttribute('aria-live', 'polite'); log.setAttribute('aria-label', 'Conversa com a LIA'); log.tabIndex = 0;
    shell.appendChild(log);

    var chips = el('div', 'lia-chips');
    SUGGESTIONS.forEach(function (s) { var c = el('button', 'chip', s); c.type = 'button'; c.onclick = function () { q.value = s; q.focus(); }; chips.appendChild(c); });
    shell.appendChild(chips);

    var form = el('form', 'lia-form');
    var ql = el('label', 'label', 'Sua pergunta'); ql.setAttribute('for', 'lia-q'); form.appendChild(ql);
    var q = el('textarea', 'field'); q.id = 'lia-q'; q.rows = 3; q.maxLength = 4000; q.placeholder = 'Pergunte sobre a aula, um erro ou um conceito…'; form.appendChild(q);
    var det = el('details', 'lia-code-details'); det.appendChild(el('summary', '', 'Colar código para a LIA analisar (opcional)'));
    det.appendChild(select('lia-lang', LANGS, 'python', 'Linguagem do código'));
    var codeLabel = el('label', 'label', 'Seu código'); codeLabel.setAttribute('for', 'lia-code'); det.appendChild(codeLabel);
    var code = el('textarea', 'field editor'); code.id = 'lia-code'; code.rows = 6; code.maxLength = 6000; code.spellcheck = false; det.appendChild(code);
    form.appendChild(det);
    var row = el('div', 'lia-sendrow');
    var send = el('button', 'btn', 'Enviar para a LIA ↗'); send.type = 'submit'; row.appendChild(send);
    row.appendChild(el('span', 'small', 'Não envie senhas nem dados pessoais. Confira sempre o código antes de usar.'));
    form.appendChild(row); shell.appendChild(form);

    var err = el('p', 'lia-error', ''); err.setAttribute('role', 'alert'); shell.appendChild(err);

    // cursos e aulas
    var courseSel = d.getElementById('lia-course'), lessonSel = d.getElementById('lia-lesson');
    try {
      var courses = await call('/data/courses');
      courses.forEach(function (c) { var o = el('option', '', c.name); o.value = c.id; courseSel.appendChild(o); });
    } catch (e) {}
    async function loadLessons(cid, pick) {
      lessonSel.textContent = ''; var o0 = el('option', '', 'Nenhuma aula'); o0.value = ''; lessonSel.appendChild(o0);
      if (!cid) return;
      try {
        var c = await call('/data/course/' + encodeURIComponent(cid));
        (c.lessons || []).forEach(function (l) { var o = el('option', '', (l.locked ? '🔒 ' : '') + l.title); o.value = l.id; if (l.locked) o.disabled = true; lessonSel.appendChild(o); });
        if (pick) lessonSel.value = pick;
      } catch (e) {}
    }
    courseSel.onchange = function () { loadLessons(courseSel.value); };
    var wanted = new URLSearchParams(location.search).get('aula');
    try {
      var plan = await call('/data/plan'); var next = plan.plan && plan.plan.next;
      if (!wanted && next) { wanted = next.id; }
      if (plan.plan && plan.plan.level) { var lv = String(plan.plan.level).toLowerCase(); if (!localStorage.getItem('ce-lia-level')) d.getElementById('lia-level').value = lv.indexOf('avan') === 0 ? 'avancado' : lv.indexOf('inter') === 0 ? 'intermediario' : 'iniciante'; }
    } catch (e) {}
    if (wanted && wanted.lastIndexOf('-') > 0) {
      var cidw = wanted.slice(0, wanted.lastIndexOf('-'));
      if (Array.prototype.some.call(courseSel.options, function (o) { return o.value === cidw; })) { courseSel.value = cidw; await loadLessons(cidw, wanted); }
    }
    d.getElementById('lia-level').onchange = function (e) { lsSet('ce-lia-level', e.target.value); };

    // histórico + status
    try {
      var h = await call('/data/lia/history');
      h.messages.forEach(function (m) { addBubble(log, m.role, m.body); });
      st.textContent = h.configured ? (h.provider === 'ollama-cloud' ? 'Ollama Cloud • configurado' : 'Ollama local • configurado') : 'Modo educativo local disponível';
      if (!h.configured) { err.textContent = 'Para respostas generativas, a administradora deve configurar o Ollama. O modo educativo local continua disponível.'; }
    } catch (e) { st.textContent = 'Não consegui carregar o histórico.'; }
    checkConnection();
    if (!log.children.length) addBubble(log, 'assistant', (typeof me!=='undefined'&&me?.account_type==='company'?'Olá! Sou a LIA Business. Posso ajudar a melhorar anúncios, organizar entrevistas e planejar a comunicação da empresa.':'Oi! Eu sou a LIA, sua tutora de programação. Pergunte sobre uma aula ou cole um código para eu analisar.'));

    clear.onclick = async function () {
      if (!confirm('Apagar definitivamente seu histórico de conversas com a LIA?')) return;
      try { await call('/data/lia/history', 'DELETE'); log.textContent = ''; addBubble(log, 'assistant', 'Conversa apagada. Como posso ajudar agora?'); st.textContent = 'Histórico apagado.'; } catch (e) { err.textContent = e.message; }
    };
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
    form.onsubmit = async function (e) {
      e.preventDefault(); var text = q.value.trim(); if (!text) return;
      err.textContent = ''; send.disabled = true; addBubble(log, 'user', text); q.value = ''; var t = typing(log);
      try {
        var x = await call('/data/lia/chat', 'POST', { question: text, level: d.getElementById('lia-level').value, mode: d.getElementById('lia-mode').value, lesson_id: lessonSel.value, code: code.value, language: d.getElementById('lia-lang').value });
        t.remove(); addBubble(log, 'assistant', x.answer); st.textContent=x.provider==='local-educational'?'Modo educativo local • histórico salvo':x.provider==='ollama-cloud'?'Ollama Cloud • histórico salvo':'Ollama local • histórico salvo'; code.value = '';
      } catch (ex) { t.remove(); q.value=text; st.textContent='Falha ao gerar resposta'; err.textContent = ex.message; }
      finally { send.disabled = false; q.focus(); }
    };
  }

  // ---------- Botão flutuante de ajuda (aulas, laboratório, desafios…) ----------
  function currentLesson() {
    var lid = '', label = '';
    if (pageName === 'course' && typeof activeLesson === 'string' && activeLesson) {
      lid = activeLesson; var h = d.querySelector('#lesson-panel h2'); label = h ? h.textContent : 'Aula atual';
    } else if (pageName === 'lab') {
      var a = new URLSearchParams(location.search).get('aula'); if (a) { lid = a; label = 'Aula aberta no laboratório'; }
    }
    return { id: lid, label: label };
  }
  function drawer() {
    var fab = el('button', 'lia-fab'); fab.type = 'button'; fab.id = 'lia-fab';
    fab.setAttribute('aria-expanded', 'false'); fab.setAttribute('aria-controls', 'lia-drawer');
    fab.innerHTML = '<span class="lia-fab-ico" aria-hidden="true">✦</span><span class="lia-fab-lbl">Ajuda da LIA</span>';
    var box = el('section', 'lia-drawer'); box.id = 'lia-drawer'; box.hidden = true; box.setAttribute('role', 'dialog'); box.setAttribute('aria-labelledby', 'lia-dtitle');
    var hd = el('div', 'lia-dhead');
    var t = el('div'); var h2 = el('strong', '', 'LIA • tutora IA'); h2.id = 'lia-dtitle'; t.appendChild(h2);
    var ctx = el('p', 'small', ''); ctx.id = 'lia-dctx'; t.appendChild(ctx); hd.appendChild(t);
    var close = el('button', 'lia-dclose', '✕'); close.type = 'button'; close.setAttribute('aria-label', 'Fechar a LIA'); hd.appendChild(close);
    box.appendChild(hd);
    var log = el('div', 'lia-log lia-dlog'); log.setAttribute('role', 'log'); log.setAttribute('aria-live', 'polite'); log.setAttribute('aria-label', 'Conversa com a LIA'); log.tabIndex = 0; box.appendChild(log);
    var err = el('p', 'lia-error', ''); err.setAttribute('role', 'alert'); box.appendChild(err);
    var form = el('form', 'lia-dform');
    var sets = el('div', 'lia-dsets');
    sets.appendChild(select('lia-dlevel', LEVELS, lsGet('ce-lia-level', 'iniciante'), 'Nível'));
    sets.appendChild(select('lia-dmode', MODES, 'hint', 'Ajuda'));
    form.appendChild(sets);
    var withCode = null;
    if (pageName === 'lab') {
      var cl = el('label', 'lia-check'); withCode = el('input'); withCode.type = 'checkbox'; withCode.checked = true; cl.appendChild(withCode); cl.appendChild(d.createTextNode(' Enviar o código do meu editor')); form.appendChild(cl);
    }
    var ql = el('label', 'sr-only', 'Pergunte à LIA'); ql.setAttribute('for', 'lia-dq'); form.appendChild(ql);
    var q = el('textarea', 'field'); q.id = 'lia-dq'; q.rows = 3; q.maxLength = 4000; q.placeholder = 'Qual é a sua dúvida?'; form.appendChild(q);
    var row = el('div', 'lia-dsend'); var send = el('button', 'btn', 'Enviar ↗'); send.type = 'submit'; row.appendChild(send);
    var more = el('a', 'link small', 'Abrir página da LIA'); more.href = '/lia'; row.appendChild(more); form.appendChild(row);
    box.appendChild(form);
    d.body.appendChild(fab); d.body.appendChild(box);

    var loaded = false;
    async function open() {
      box.hidden = false; fab.setAttribute('aria-expanded', 'true');
      var c = currentLesson(); ctx.textContent = c.id ? 'Aula: ' + c.label : 'Sem aula selecionada — pergunta geral';
      if (!loaded) {
        loaded = true;
        if (!isLogged()) { log.innerHTML = '<div class="empty">Entre na sua conta para falar com a LIA. <a class="link" href="/entrar">Entrar →</a></div>'; form.hidden = true; }
        else {
          try { var h = await call('/data/lia/history'); h.messages.slice(-8).forEach(function (m) { addBubble(log, m.role, m.body); }); if (!h.configured) err.textContent = 'A LIA ainda não foi ativada neste servidor.'; } catch (e) {}
          if (!log.children.length) addBubble(log, 'assistant', 'Oi! Estou aqui para ajudar com esta aula. Conte onde travou e eu te dou uma pista. 💜');
        }
      }
      q.focus();
    }
    function shut() { box.hidden = true; fab.setAttribute('aria-expanded', 'false'); fab.focus(); }
    fab.onclick = function () { box.hidden ? open() : shut(); };
    close.onclick = shut;
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !box.hidden) shut(); });
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
    form.onsubmit = async function (e) {
      e.preventDefault(); var text = q.value.trim(); if (!text) return;
      var c = currentLesson(); ctx.textContent = c.id ? 'Aula: ' + c.label : 'Sem aula selecionada — pergunta geral';
      var body = { question: text, level: d.getElementById('lia-dlevel').value, mode: d.getElementById('lia-dmode').value, lesson_id: c.id };
      if (withCode && withCode.checked) { var ta = d.getElementById('code'), lg = d.getElementById('lang'); if (ta && ta.value.trim()) { body.code = ta.value.slice(0, 6000); body.language = lg ? lg.value : ''; } }
      err.textContent = ''; send.disabled = true; addBubble(log, 'user', text); q.value = ''; var tp = typing(log);
      try { var x = await call('/data/lia/chat', 'POST', body); tp.remove(); addBubble(log, 'assistant', x.answer); }
      catch (ex) { tp.remove(); err.textContent = ex.message; }
      finally { send.disabled = false; q.focus(); }
    };
  }

  window.LIA = { page: page };
  if (pageName !== 'tutor' && pageName !== 'auth' && pageName !== 'verify' && pageName !== 'admin') {
    if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', drawer); else drawer();
  }
})();
