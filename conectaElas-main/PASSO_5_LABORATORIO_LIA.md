# PASSO 5 — Laboratório + LIA

Versão cumulativa: PASSOS 1 a 5.

- Botão Corrigir com LIA e opções: depuração, explicação linha por linha, dicas de exercícios e explicação geral.
- A análise usa `/data/lia/chat`, enviando linguagem, código e identificador da aula, quando disponível.
- A LIA só responde quando ANTHROPIC_API_KEY estiver configurada no servidor e o pacote anthropic instalado. Não há resposta de IA simulada.
- O editor já oferece validação de sintaxe Python, Java, JSON e JavaScript; resultados e prévia HTML/CSS; testes de JavaScript em iframe com sandbox; SQL em base temporária somente leitura; salvamento de projetos no SQLite e carregamento de exercícios via `?aula=ID`.
- A validação Python/Java NÃO executa código no servidor. A execução Python e Java continua indisponível por segurança, até existir infraestrutura de sandbox separada e testada.
- Não cole segredos nos códigos enviados à LIA.
- Para testar: instale dependências, configure a chave no ambiente, inicie Flask, faça login, abra Laboratório e teste os modos e o salvamento.
