# PASSO 9 — Portfólio dentro do Perfil

Base: ConectaElas PASSOS 1 a 8. Todas as funcionalidades anteriores foram mantidas.

- Removido link do portfólio do menu lateral; a rota antiga /portfolio abre a página Perfil.
- Nova seção Meu Portfólio no Perfil, com abas Projetos, Habilidades e conquistas, Compartilhar e privacidade.
- Lista projetos publicados no PASSO 7, com destaque persistido no SQLite e botão para editar/publicar na página Projetos.
- Exibe linguagens, tecnologias, certificados reais e informação de conquistas.
- Configura links HTTPS do GitHub e LinkedIn.
- Publicação opt-in: o link é privado por padrão. O servidor aplica permissões de visibilidade para bio, habilidades, projetos, certificados e conquistas.
- Link aleatório /p/<token> pode ser copiado, desativado e regenerado para invalidar o antigo.
- Tabela portfolio_settings criada automaticamente na inicialização, sem apagar dados existentes.
- API pública não inclui e-mail, senhas, tokens de login ou histórico da LIA.
- Layout responsivo para telas pequenas.

## Verificação

- `python -m py_compile app.py`
- `node --check static/app.js`
- Testar no navegador com uma conta de aluna: criar projeto, destacar, acessar Perfil, ativar publicação, abrir link em janela anônima, desativar publicação, verificar 404 e regenerar token.
- Os testes integrados com Flask não foram executados neste ambiente, pois Flask não está instalado.

## Observações

- Imagens de projetos permanecem por URL HTTPS, como no PASSO 7, não upload.
- O conteúdo do portfólio público depende exclusivamente dos controles de privacidade da usuária.
- A LIA local e as páginas anteriores não foram alteradas.
