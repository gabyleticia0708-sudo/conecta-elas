# PASSO 8 — Encontrar Empregos

Atualização cumulativa a partir do ZIP do PASSO 7.

- Abas independentes: Oportunidades, Favoritas, Minhas candidaturas (alunas), Área da empresa e Candidaturas recebidas (contratantes).
- Pesquisa por cargo, organização, tecnologia, categoria, modalidade e localização.
- Cartões padronizados, com destaque de cargo, empresa, modalidade, localização e link para requisitos completos.
- Favoritos mantidos pelo endpoint SQL já existente.
- Candidaturas registradas e consultadas pelos endpoints existentes.
- Contratantes continuam podendo publicar, editar e excluir seus anúncios.
- Layout responsivo para telas pequenas e navegação por abas com estado acessível.
- Mantidos os demais arquivos e a LIA local dos passos anteriores.

## Testes recomendados

1. Abrir oportunidades sem login; filtrar e visualizar detalhes.
2. Entrar como aluna; salvar uma vaga e verificar Favoritas; candidatar-se e consultar Minhas candidaturas.
3. Entrar como contratante; publicar, editar, excluir e consultar candidaturas recebidas.
4. Testar em celular e com teclado.

Validação realizada: `node --check static/app.js` e `python -m py_compile app.py`. Fluxos Flask e banco não foram testados em execução neste ambiente.
