# ConectaElas — LIA com Ollama

A LIA principal, o laboratório e as rotas antigas de tutoria utilizam exclusivamente Ollama. Não há respostas prontas em caso de falha de conexão. O histórico principal continua separado por conta no SQLite. Código e mensagens são enviados ao servidor Ollama selecionado; não compartilhe segredos ou dados pessoais.

## Local (VS Code / Codespaces)
Instale Ollama seguindo https://ollama.com/download. Em um terminal, execute `ollama serve` se o serviço ainda não estiver rodando. Em outro, execute:

```
ollama pull llama3.2:1b
python -m pip install -r requirements.txt
python app.py
```

Por padrão, usa `http://127.0.0.1:11434` e `llama3.2:1b`. Não exponha a porta 11434 publicamente.

## Render gratuito (Ollama Cloud)
Configure um Web Service Python com build `pip install -r requirements.txt` e start `gunicorn --timeout 120 app:app`. No painel Environment configure:

- `OLLAMA_URL=https://ollama.com`
- `OLLAMA_MODEL` = identificador exato de um modelo Cloud disponível na sua conta (consulte https://ollama.com/search?c=cloud).
- `OLLAMA_API_KEY` = chave criada em https://ollama.com/settings/keys (somente no servidor).
- `SECRET_KEY` = valor longo e aleatório, gerado com `python -c "import secrets; print(secrets.token_hex(32))"`.
- `COOKIE_SECURE=1`
- `FLASK_ENV=production`

O modo Cloud depende da disponibilidade, limites e condições da conta. Não use o nome do modelo local presumindo que existe na nuvem. Não coloque chaves no GitHub.

**Atenção:** o banco continua SQLite, como na versão anterior. O armazenamento do Render gratuito é efêmero e pode perder cadastros, conversas e progresso em reinicializações/deploys. Não use com dados reais de alunas antes de configurar armazenamento persistente e revisar privacidade, segurança e moderação. A migração para PostgreSQL não está incluída neste ZIP. O limite de mensagens é por processo e não substitui cotas globais em produção.

## Testes
`python -m unittest discover -s tests -v` após instalar dependências. Testes de Ollama simulam a API; não comprovam conexão real com a nuvem.
