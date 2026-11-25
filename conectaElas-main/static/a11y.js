/* Acessibilidade global do ConectaElas.
   Usa as mesmas chaves/classes que os botões do topo (ce-theme, ce-contrast, ce-motion, ce-size),
   então painel lateral e topo ficam sempre sincronizados. */
(function () {
  'use strict';
  var K = { theme: 'ce-theme', contrast: 'ce-contrast', motion: 'ce-motion', size: 'ce-size', spacing: 'ce-spacing', vlibras: 'ce-vlibras', simple: 'ce-simple' };
  var MIN = 12, MAX = 24, DEF = 16;
  var body = document.body;

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function size() { var n = Number(get(K.size) || DEF); return isFinite(n) ? Math.max(MIN, Math.min(MAX, n)) : DEF; }

  function applySize() {
    var n = size();
    document.documentElement.style.setProperty('--user-font-scale', String(n / 16));
    document.documentElement.style.fontSize = n + 'px';
  }

  // Aplica todas as preferências salvas (também é chamado cedo, antes da página desenhar)
  function applyAll() {
    var motionSaved = get(K.motion);
    var osReduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    body.classList.toggle('dark', get(K.theme) === 'dark');
    body.classList.toggle('contrast', get(K.contrast) === '1');
    body.classList.toggle('reduce-motion', motionSaved === '1' || (motionSaved === null && osReduce));
    body.classList.toggle('a11y-spacing', get(K.spacing) === '1');
    body.classList.toggle('a11y-vlibras', get(K.vlibras) === '1');
    body.classList.toggle('a11y-simple', get(K.simple) === '1');
    applySize();
  }
  applyAll();

  function announce(text) {
    var r = document.getElementById('access-announcement');
    if (!r) { r = document.createElement('div'); r.id = 'access-announcement'; r.className = 'sr-only'; r.setAttribute('role', 'status'); r.setAttribute('aria-live', 'polite'); document.body.appendChild(r); }
    r.textContent = ''; setTimeout(function () { r.textContent = text; }, 40);
  }

  // ---------- VLibras (widget oficial do governo federal) ----------
  var vlibrasLoaded = false;
  function ensureVLibras() {
    if (vlibrasLoaded || document.querySelector('[vw]')) { vlibrasLoaded = true; return; }
    vlibrasLoaded = true;
    var box = document.createElement('div');
    box.setAttribute('vw', ''); box.className = 'enabled';
    box.innerHTML = '<div vw-access-button class="active"></div><div vw-plugin-wrapper><div class="vw-plugin-top-wrapper"></div></div>';
    document.body.appendChild(box);
    var s = document.createElement('script');
    s.src = 'https://vlibras.gov.br/app/vlibras-plugin.js';
    s.onload = function () { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} };
    s.onerror = function () { announce('Não foi possível carregar o VLibras. Verifique sua conexão com a internet.'); };
    document.body.appendChild(s);
  }

  // ---------- Ações ----------
  var actions = {
    plus: function () { var n = Math.min(MAX, size() + 2); set(K.size, String(n)); applySize(); announce('Tamanho do texto: ' + Math.round(n / 16 * 100) + ' por cento'); },
    minus: function () { var n = Math.max(MIN, size() - 2); set(K.size, String(n)); applySize(); announce('Tamanho do texto: ' + Math.round(n / 16 * 100) + ' por cento'); },
    reset: function () { set(K.size, String(DEF)); applySize(); announce('Tamanho do texto padrão'); },
    contrast: function () { var on = !body.classList.contains('contrast'); body.classList.toggle('contrast', on); set(K.contrast, on ? '1' : '0'); announce('Alto contraste ' + (on ? 'ativado' : 'desativado')); },
    dark: function () { var on = !body.classList.contains('dark'); body.classList.toggle('dark', on); set(K.theme, on ? 'dark' : 'light'); announce('Modo escuro ' + (on ? 'ativado' : 'desativado')); },
    simple: function () { var on = !body.classList.contains('a11y-simple'); body.classList.toggle('a11y-simple', on); set(K.simple, on ? '1' : '0'); announce('Leitura simplificada ' + (on ? 'ativada' : 'desativada')); },
    spacing: function () { var on = !body.classList.contains('a11y-spacing'); body.classList.toggle('a11y-spacing', on); set(K.spacing, on ? '1' : '0'); announce('Espaçamento ampliado ' + (on ? 'ativado' : 'desativado')); },
    motion: function () { var on = !body.classList.contains('reduce-motion'); body.classList.toggle('reduce-motion', on); set(K.motion, on ? '1' : '0'); announce('Animações ' + (on ? 'reduzidas' : 'habilitadas')); },
    vlibras: function () { var on = !body.classList.contains('a11y-vlibras'); body.classList.toggle('a11y-vlibras', on); set(K.vlibras, on ? '1' : '0'); if (on) ensureVLibras(); announce('VLibras ' + (on ? 'ativado. Use o botão de mãos que apareceu na lateral.' : 'desativado')); },
    all: function () {
      Object.keys(K).forEach(function (k) { try { localStorage.removeItem(K[k]); } catch (e) {} });
      body.classList.remove('dark', 'contrast', 'reduce-motion', 'a11y-spacing', 'a11y-vlibras', 'a11y-simple');
      applyAll(); announce('Configurações de acessibilidade restauradas');
    }
  };

  // ---------- Painel ----------
  var TOGGLES = [
    ['contrast', 'Alto contraste', 'contrast'],
    ['dark', 'Modo escuro', 'dark'],
    ['spacing', 'Espaçamento de letras e linhas', 'a11y-spacing'],
    ['simple', 'Leitura simplificada', 'a11y-simple'],
    ['motion', 'Reduzir animações', 'reduce-motion'],
    ['vlibras', 'VLibras (tradução em Libras)', 'a11y-vlibras']
  ];

  function build() {
    var tab = document.createElement('button');
    tab.type = 'button'; tab.className = 'a11y-tab'; tab.id = 'a11y-tab';
    tab.setAttribute('aria-expanded', 'false'); tab.setAttribute('aria-controls', 'a11y-panel'); tab.setAttribute('aria-label', 'Acessibilidade'); tab.title = 'Acessibilidade';
    tab.innerHTML = '<span class="a11y-ico" aria-hidden="true">♿</span><span class="a11y-lbl">Acessibilidade</span>';

    var panel = document.createElement('div');
    panel.className = 'a11y-panel'; panel.id = 'a11y-panel'; panel.hidden = true;
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-labelledby', 'a11y-title');

    var html = '<div class="a11y-head"><h2 id="a11y-title">Acessibilidade</h2><button type="button" class="a11y-close" aria-label="Fechar painel de acessibilidade">✕</button></div>' +
      '<p class="a11y-sub">Ajuste o site ao seu jeito. Suas escolhas ficam salvas em todas as páginas.</p>' +
      '<div class="a11y-group"><span class="a11y-gt">TAMANHO DO TEXTO</span><div class="a11y-size">' +
      '<button type="button" class="a11y-btn" data-a="minus" aria-label="Diminuir texto">A−</button>' +
      '<button type="button" class="a11y-btn" data-a="reset" aria-label="Tamanho padrão do texto">A</button>' +
      '<button type="button" class="a11y-btn" data-a="plus" aria-label="Aumentar texto">A+</button></div>' +
      '<span class="a11y-note" id="a11y-size-info"></span></div>' +
      '<div class="a11y-group"><span class="a11y-gt">VISUAL E LEITURA</span>';
    TOGGLES.forEach(function (t) {
      html += '<button type="button" class="a11y-btn" data-a="' + t[0] + '" data-cls="' + t[2] + '" aria-pressed="false"><span>' + t[1] + '</span><span class="a11y-state" aria-hidden="true"></span></button>';
    });
    html += '</div><button type="button" class="a11y-btn a11y-reset" data-a="all">Restaurar padrão</button>' +
      '<p class="a11y-note">O VLibras é o tradutor oficial para Libras e precisa de internet.</p>';
    panel.innerHTML = html;

    document.body.appendChild(tab);
    document.body.appendChild(panel);

    function refresh() {
      panel.querySelectorAll('[data-cls]').forEach(function (b) {
        var on = body.classList.contains(b.dataset.cls);
        b.setAttribute('aria-pressed', String(on));
        b.querySelector('.a11y-state').textContent = on ? 'LIGADO' : 'DESLIGADO';
      });
      var info = panel.querySelector('#a11y-size-info');
      if (info) info.textContent = 'Texto em ' + Math.round(size() / 16 * 100) + '%';
    }
    function open() { panel.hidden = false; tab.setAttribute('aria-expanded', 'true'); refresh(); var f = panel.querySelector('.a11y-close'); if (f) f.focus(); }
    function close(back) { panel.hidden = true; tab.setAttribute('aria-expanded', 'false'); if (back) tab.focus(); }

    tab.addEventListener('click', function () { panel.hidden ? open() : close(true); });
    panel.addEventListener('click', function (e) {
      if (e.target.closest('.a11y-close')) { close(true); return; }
      var b = e.target.closest('[data-a]');
      if (b && actions[b.dataset.a]) { actions[b.dataset.a](); refresh(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(true); });
    // mantém o painel sincronizado com os botões do topo
    new MutationObserver(refresh).observe(body, { attributes: true, attributeFilter: ['class'] });
    new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ['style'] });
    refresh();
  }

  // Sincronização opcional com o perfil autenticado; armazenamento local continua disponível offline.
  var syncing = false;
  function currentPrefs() {
    var out = {}; Object.keys(K).forEach(function (k) { out[k] = get(K[k]); }); return out;
  }
  function saveProfilePrefs() {
    if (syncing) return;
    fetch('/data/profile/preferences', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({accessibility:currentPrefs()})}).catch(function(){});
  }
  function loadProfilePrefs() {
    fetch('/data/profile/preferences',{credentials:'same-origin'}).then(function(r){if(!r.ok)throw Error('Não autenticada');return r.json();}).then(function(data){
      var saved=data.accessibility || {};
      if (!Object.keys(saved).length) { saveProfilePrefs(); return; }
      syncing=true;
      Object.keys(K).forEach(function(k){if(saved[k] !== undefined && saved[k] !== null)set(K[k],String(saved[k]));});
      applyAll(); syncing=false;
    }).catch(function(){});
  }
  function ready() {
    build();
    loadProfilePrefs();
    document.getElementById('a11y-panel').addEventListener('click',function(e){if(e.target.closest('[data-a]'))setTimeout(saveProfilePrefs,0);});
    if (get(K.vlibras) === '1') ensureVLibras();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();

  window.CEAccess = { applyAll: applyAll, sync: loadProfilePrefs };
})();
