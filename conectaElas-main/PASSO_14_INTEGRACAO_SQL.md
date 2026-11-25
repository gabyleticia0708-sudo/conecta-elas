# PASSO 14 — Integração SQLite

- Cursos e aulas: catálogo normalizado em `catalog_courses` e `catalog_lessons`; `curriculo.json` usado apenas na primeira inicialização.
- Personalizações administrativas antigas são migradas para as novas tabelas, sem descartar registros de progresso.
- Edição de curso/aula sincroniza catálogo SQL na mesma transação da alteração administrativa.
- Correção da avaliação de aulas criadas no painel: campo `correct` e explicação `quizExplanation` compatíveis com os exercícios existentes.
- Matrículas são registradas junto com respostas e a visão geral mostra cursos iniciados mesmo antes da primeira conclusão.
- Não são mais geradas vagas ilustrativas automaticamente em bancos novos.
- Login de administradores autorizados encaminha ao painel administrativo.
- Permanecem no SQLite: cadastros, autenticação, progresso, exercícios, desafios, certificados, projetos, portfólio, vagas, candidaturas, comunidade e preferências de acessibilidade.

## Limites
- O aplicativo usa SQLite (SQL), não um servidor PostgreSQL/MySQL.
- As tabelas legadas `admin_course_data` são preservadas para compatibilidade; não devem ser editadas manualmente após a migração.
- Não foi possível executar os testes HTTP com Flask neste ambiente sem dependências; consulte o relatório de verificação.
- Vagas ilustrativas previamente presentes no banco legado não são apagadas automaticamente para evitar perda de dados.
