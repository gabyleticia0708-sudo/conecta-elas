# PASSO 15 — Design e verificações finais

## Alterações aplicadas
- Preservada a paleta roxa, sem substituição dos estilos existentes.
- Refinados espaçamentos, cartões, botões, menu lateral, foco, responsividade e áreas de toque.
- Criado estado vazio personalizado para certificados; demais estados vazios existentes foram preservados.
- Respeitada a preferência de reduzir animações.
- Mantidas as rotas, o esquema SQL, a LIA local e os recursos dos passos anteriores.

## Testes possíveis neste ambiente
- Compilação estática de arquivos Python.
- Verificação de sintaxe JavaScript com Node, quando disponível.
- Validação de arquivos ZIP e integridade SQLite.
- Verificação de presença das principais rotas e arquivos.

## Pendências que NÃO foram validadas
- Fluxos de login/cadastro, cursos, trilhas, desafios, laboratório, LIA, projetos, portfólio, comunidade, contratantes e admin em servidor Flask.
- Auditoria WCAG 2.2 com leitor de tela, teclado e celular real.
- Testes de autorização e proteção de dados em ambiente de produção.

**Motivo:** Flask não está instalado no ambiente de verificação e a instalação de dependências via rede está indisponível. Não declarar testes funcionais concluídos.

## Como testar no Codespaces
```bash
pip install -r requirements.txt
python -m pytest -q
python app.py
```
Depois, percorra os fluxos com contas de aluna, contratante e administradora autorizada, usando um banco de testes. Não envie dados pessoais de teste ao GitHub.
