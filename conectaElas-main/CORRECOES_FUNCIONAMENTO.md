# Correções de funcionamento
- Cursos: avanço após resposta correta sem reabrir aula concluída indicada por URL; carregamento de projetos e conteúdos opcionais tolerante a campos ausentes; atualização da versão dos scripts para evitar cache antigo.
- Vagas: candidaturas por anúncio, contador e filtro de recebidas, atualização manual e prevenção de envio duplicado. Anúncios demonstrativos não recebem candidaturas. Teste usando duas contas distintas, uma contratante que publica e outra candidata.
- LIA: botão Testar conexão, verificação de modelo via /api/tags, preservação da mensagem em caso de erro, URL normalizada e configuração de nuvem automaticamente quando há chave e nenhuma URL explícita. Não há fallback para outro provedor.

Render: build `pip install -r requirements.txt`; start `gunicorn --workers 1 --threads 4 --timeout 120 app:app`. Configure OLLAMA_URL=https://ollama.com, OLLAMA_MODEL com identificador disponível na conta e OLLAMA_API_KEY como segredo. Em local, use ollama serve e ollama pull llama3.2:1b. Veja CONFIGURAR_OLLAMA.md. SQLite permanece; o armazenamento gratuito do Render não é persistente.

Validação: quatro testes de avaliação e dois testes simulados de transporte Ollama passaram; sintaxe Python/JS conferida. Flask não está instalado no ambiente de edição e não foi possível instalar dependências; testes completos de navegador, candidaturas HTTP e conexão real com Ollama não foram realizados.
