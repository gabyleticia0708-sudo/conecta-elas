# Etapa 13 — LIA e acessibilidade global

## LIA
- `lia_ai.py`: prompt de sistema da LIA, níveis (iniciante/intermediária/avançada), modos (explicar, linha por linha, corrigir, só pistas), limite de uso e chamada à API.
- `app.py`: rotas `/data/lia/chat`, `/data/lia/history` (GET/DELETE), `/data/lia/status`; tabela `lia_messages`; página `/lia` (a rota `/tutora` continua funcionando).
- `static/lia.js` e `static/lia.css`: página exclusiva, botão flutuante "Ajuda da LIA" (aulas, laboratório e demais páginas), envio do código do editor, respostas com blocos de código e botão copiar.
- Tutora antiga (`/data/tutor/*`) foi mantida no backend, sem alterações.

## Acessibilidade
- `static/a11y.js` e `static/a11y.css`: aba lateral e painel com aumentar/diminuir fonte, alto contraste, modo escuro, espaçamento, reduzir animações, VLibras e restaurar padrão.
- Preferências em `localStorage`; sincronizadas com os botões do topo.

## Correções feitas no caminho
- `app.py`: o bloco `if __name__=='__main__'` estava no meio do arquivo, então rodar `python app.py` não carregava as rotas definidas depois dele. Agora está no fim.
- `style.css`: "reduzir animações" desligava todos os `transform`, deixando o link "Pular para o conteúdo" sempre visível. Agora só desliga os efeitos de hover.

## Testes
`python -m unittest discover -s tests -v`. Os testes da LIA (`tests/test_lia.py`) usam IA simulada. Obs.: `test_certificate_lock_and_pdf` já falhava antes desta etapa.
