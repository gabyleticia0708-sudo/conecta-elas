# Avaliações, práticas e favicon

- 702 questões diferentes em 23 cursos, com alternativas em ordem variada.
- 86 projetos/atividades de módulo, independentes da prova objetiva.
- Próxima aula: exige acerto na questão da aula anterior. Próximo módulo: todas as aulas e avaliação de múltipla escolha com no mínimo 70%.
- Cada aula oferece entrega opcional de atividade e integração com o laboratório. A avaliação do módulo pode ser enviada sem entrega prática. Não há questão discursiva nem campo obrigatório de anotações de teste.
- O SQL registra entregas, notas e tentativas. A revisão pela LIA usa Ollama (conforme configuração anterior). O servidor não executa código arbitrário; a entrega do código não comprova automaticamente que ele funciona. A nota é calculada a partir das questões objetivas.
- Favicon PNG e ICO foram criados da imagem fornecida, mantendo a logo interna do site.
- O catálogo SQLite incluído já contém os novos enunciados. Instalações existentes recebem migração seletiva dos enunciados originais ao iniciar, sem apagar personalizações ou progresso anterior.

## Executar

`pip install -r requirements.txt`

`python app.py`

Consulte CONFIGURAR_OLLAMA.md para configurar o provedor de IA. Nenhuma chave é necessária para realizar as avaliações objetivas e registrar entregas práticas; a revisão com LIA depende da configuração do Ollama.

## Verificação

`python -m unittest discover -s tests -p 'test_assessment_engine.py' -v`

`python -m unittest discover -s tests -v` (requer as dependências do projeto).
