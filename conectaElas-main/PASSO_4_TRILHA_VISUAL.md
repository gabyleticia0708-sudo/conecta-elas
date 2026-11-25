# PASSO 4 — Trilha visual

- Caminho vertical com etapas circulares conectadas e alternadas.
- Estados de aula concluída, disponível e bloqueada calculados pelo backend existente.
- Ícones de módulos, avaliação e conquistas ao concluir módulos.
- Clique em etapas disponíveis abre a aula correspondente; bloqueadas ficam desabilitadas.
- Animações discretas e respeito à preferência por movimento reduzido.
- Progresso continua sendo salvo pelo endpoint de resposta da aula no SQLite; nenhum dado existente é apagado.
- Preserva as mudanças dos passos 1, 2 e 3.

Verificações automáticas: sintaxe JavaScript e Python. Teste de navegação e conclusão de aulas deve ser feito com o servidor Flask em execução.
