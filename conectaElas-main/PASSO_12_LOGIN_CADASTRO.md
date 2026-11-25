# PASSO 12 — Login e Cadastro

- Cadastro em três etapas, perguntas opcionais e dados salvos em users no SQLite.
- Somente tipos student e employer são aceitos pelo backend. Administração é concedida exclusivamente via tabela admins.
- Redirecionamento decidido pelo servidor segundo o tipo de conta.
- Menu de conta com foto/nome, perfil, configurações e sair.
- Cookies HttpOnly, SameSite Lax e duração máxima de sessão de 7 dias. Em produção configurar SECRET_KEY e COOKIE_SECURE=1 com HTTPS.
- Mantidos LIA local, cursos, desafios, projetos, empregos e demais passos.

Testar cadastro e login de ambos os perfis, logout, restauração de sessão, privacidade e administração em Codespaces.
