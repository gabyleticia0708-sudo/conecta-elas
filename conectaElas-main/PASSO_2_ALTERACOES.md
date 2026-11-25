# PASSO 2 — Cursos e Trilhas

Base: ZIP do PASSO 1. Preservadas as outras páginas, LIA, login, acessibilidade e banco de dados.

1. Sem cartões de estatísticas gerais no catálogo de cursos.
2. Estatísticas permanecem na Visão Geral e Perfil.
3. Cursos agrupados por categoria/linguagem.
4. Filtros por nível, área, situação e favoritos.
5. Estados não iniciado, em andamento e concluído calculados pelo SQL.
6. Botões Iniciar, Continuar e Revisar.
7. Início de curso registrado na tabela course_enrollments; conclusão de aulas permanece registrada na tabela completions após avaliação correta.
8. Cartões e filtros redesenhados mantendo paleta roxa e responsividade.

Para testar: pip install -r requirements.txt; python app.py. A tabela é criada automaticamente na inicialização.
