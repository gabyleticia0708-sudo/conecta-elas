# ConectaElas — estado das 15 melhorias

Base: versão parcial fornecida anteriormente. As alterações existentes foram preservadas.

1. Visão geral: estado vazio e progresso real já implementados na base; barras ilustrativas da lateral removidas.
2. Cursos: filtros por nível e categoria e progresso real presentes; filtro de duração ainda pendente.
3. Desafios: exibidos somente para cursos em andamento na base.
4. Trilha: plano persistido e estados de módulo; refinamento visual parcial (não é uma reprodução integral do Duolingo).
5. Laboratório: novo botão Corrigir com LIA envia código à rota de tutoria; execução isolada existente preservada.
6. LIA: integração por OPENAI_API_KEY já existia. Sem chave, modo local é explicitamente identificado, não IA generativa.
7. Projetos: ideias e publicação via portfólio existentes; novos destaques no banco e API.
8. Empregos: busca/filtros, gestão empresarial existentes; candidaturas persistidas, painel da aluna e da empresa adicionados. Vagas demonstrativas não aceitam candidatura.
9. Portfólio: link da navegação aponta para Perfil; a tela própria antiga ainda existe para compatibilidade. Integração visual total ao perfil pendente.
10. Comunidade: tópicos, publicações, denúncias, moderação e bloqueios existentes; sistema de conexões diretas ainda não concluído.
11. Perfil: biografia, avatar por URL, interesses, alteração de senha presentes; upload de imagem ainda pendente.
12. Login/cadastro: perfis de aluna/empresa e controle de administrador já presentes. Cadastro por etapas ainda pendente.
13. Acessibilidade: fonte, contraste, tema, movimento reduzido e recursos já existentes. Auditoria WCAG 2.2 integral pendente.
14. Integração: banco SQLite existente, novas tabelas e endpoints; testes de ponta a ponta pendentes.
15. Design: ajustes pontuais de CSS e foco; revisão integral de todas as telas pendente.

## Limitações e implantação
- Este ZIP NÃO representa conclusão integral dos 15 requisitos. Ele inclui avanços reais sobre a versão parcial.
- Instale as dependências com `pip install -r requirements.txt` e rode `python app.py`.
- Para respostas generativas da LIA configure `OPENAI_API_KEY` no ambiente do servidor. Nunca publique a chave no GitHub.
- Testes executados neste ambiente: compilação Python e checagem de sintaxe JavaScript. Flask não estava instalado para testes de integração.
- Faça backup de `conectas.db` antes de implantar. O projeto inclui banco preexistente; evite publicar dados pessoais.
