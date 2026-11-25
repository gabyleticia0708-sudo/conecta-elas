# Publicação no Render

Use o render.yaml ou crie um Web Service Python. Build: `pip install -r requirements.txt`. Start: `gunicorn --workers 1 --threads 4 --timeout 90 --bind 0.0.0.0:$PORT app:app`.

Configure SECRET_KEY (valor aleatório longo e privado), FLASK_ENV=production, COOKIE_SECURE=1. Nunca envie chaves ao GitHub. Para testar sem IA generativa, LIA_LOCAL_FALLBACK=1 permite respostas educativas locais identificadas. Para Ollama Cloud, configure OLLAMA_URL=https://ollama.com, OLLAMA_API_KEY e OLLAMA_MODEL (modelo disponível na sua conta). Verifique os termos, elegibilidade e cotas com o responsável pela plataforma. Não envie dados pessoais ou código com segredos. Não ative cobrança se o objetivo for uso gratuito. Para VS Code, use OLLAMA_URL=http://127.0.0.1:11434 e OLLAMA_MODEL=llama3.2:1b. O modo local educativo não é um LLM.

ATENÇÃO: o SQLite e as fotos armazenadas no disco são temporários no Render gratuito. O site é executável no Render, mas não é uma implantação persistente de produção. Antes de uso real, migrar o banco para PostgreSQL externo e as fotos para armazenamento persistente, ou usar disco persistente em plano compatível. DATABASE_PATH permite apontar SQLite para um volume persistente quando disponível. Não publique o banco com dados pessoais. Não há migração PostgreSQL neste pacote.
