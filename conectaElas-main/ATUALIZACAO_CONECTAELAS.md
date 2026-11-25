# Atualização ConectaElas

Esta versão foi construída sobre os arquivos do repositório enviados, mantendo o Flask, SQLite, identidade visual, autenticação, acessibilidade e funcionalidades existentes. Não é uma reescrita do projeto.

## Alterações
- Catálogo de 23 cursos: preserva 15 existentes e adiciona 8 introdutórios (TypeScript, Vue.js, Node.js, Django, PostgreSQL, Docker, Machine Learning e Desenvolvimento Web Seguro), com 3 aulas cada, questionários e mini projeto.
- Cursos com lista convencional de módulos/aulas e exemplos comentados. Trilhas personalizadas com caminho visual e estados conforme conclusão real. A ordem visual é uma recomendação; cursos independentes continuam acessíveis pelo catálogo.
- Painel direito oculto nas demais páginas, mantido em Visão geral e Perfil em telas suficientemente largas.
- LIA local ampliada, com orientação de navegação e revisão estática; mantém integração com laboratório e provedor externo opcional. Não executa código. Se a API falhar, informa o uso do modo local.
- Salário textual opcional em anúncios, botão de candidatura na lista e detalhes, indicação de envio e status editável apenas pelo contratante dono da vaga. Não divulga e-mail de candidatas automaticamente.
- Comunidade autenticada com respostas a comentários, atualização manual do feed, notificações, bloqueio e moderação existentes.
- Cronograma personalizado com revisões de 15 min para erros ainda não superados e aulas de 35 min, dentro das horas semanais informadas.
- Migrações SQLite aditivas: salário, status e referência do comentário respondido. A carga do catálogo insere cursos novos sem sobrescrever registros existentes.

## Executar
No terminal, na pasta que contém app.py:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000 (no Codespaces, abra a porta 5000 de forma privada). Não publique a base SQLite com dados pessoais. Use uma chave SECRET_KEY própria em produção e armazenamento persistente; para acesso multiusuário real, faça revisão de segurança e moderação antes de publicar.

## Verificação
Validados: sintaxe dos módulos Python e JavaScript, integridade do SQLite, migrações aditivas, carga dos 23 cursos, cronograma com revisão dentro do orçamento semanal e revisão estática/navegação da LIA local. O ambiente de preparação não tinha Flask instalado; não foi possível testar o servidor HTTP, renderização no navegador ou chamada da API externa. Para testar localmente, use duas contas distintas para confirmar candidaturas e respostas da comunidade. As vagas demonstrativas existentes continuam identificadas como demonstração e não recebem candidaturas.
