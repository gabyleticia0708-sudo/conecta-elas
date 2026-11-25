# Acompanhamento das 15 melhorias — 22/11/2026

Este ZIP contém alterações reais sobre o projeto enviado. Não representa a implementação integral das 15 áreas.

1. Visão geral: corrigido estado inicial e exibição de continuar aprendendo.
2. Cursos: filtros existentes preservados; reorganização completa pendente.
3. Desafios: somente cursos com progresso iniciado, com estado vazio.
4. Trilha: melhorias visuais no caminho existente; progressão SQL preservada.
5. Laboratório: editor existente preservado; integração completa de correção com LIA pendente.
6. LIA: código de integração existente preservado; requer chave API e testes externos.
7. Projetos: ideias por nível e acesso à publicação externa adicionados.
8. Empregos: recursos de vagas e empresas preservados; revisão completa da interface pendente.
9. Portfólio: atalho integrado ao perfil; página separada mantida para compatibilidade.
10. Comunidade: endpoint para bloquear/desbloquear usuários criado; interface completa pendente.
11. Perfil: campos de biografia, objetivo, nível, interesses, ocupação, linguagens, foto por URL HTTPS e troca de senha.
12. Login: link entrar/cadastrar oculto após autenticação; contas e permissões anteriores preservadas.
13. Acessibilidade: preferências por conta no backend; integração de UI e auditoria WCAG pendentes.
14. Integração: novas colunas SQL com migração não destrutiva; testes funcionais pendentes.
15. Design: ajustes discretos na trilha e formulários, mantendo tons originais.

Verificações: compilação Python e sintaxe JavaScript passaram. Pytest não pôde iniciar pois Flask não está instalado neste ambiente.

Para executar: `pip install -r requirements.txt` e `python app.py`. Configure a chave de API para LIA conforme README/.env.example. Faça backup do banco antes de executar uma atualização.
