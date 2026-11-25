# PASSO 10 — Comunidade ConectaElas

Base: PASSO 9. Preservados os PASSOS 1 a 9, incluindo a LIA local.

## Implementado
- Publicações, comentários, curtidas, grupos por tecnologia, denúncias e fila de moderação (funcionalidades existentes, reorganizadas em abas).
- Perfis voluntários, privados por padrão, com descrição, habilidades e interesses; pesquisa por interesses.
- Convites de colaboração e mentoria com aceite, recusa e cancelamento, sem abrir conversas privadas ou divulgar dados pessoais.
- Notificações internas para convites, respostas e comentários, com marcação como lidas.
- Bloqueio e desbloqueio de participantes, ocultação de publicações/comentários e restrição de convites.
- Configurações individuais de privacidade persistidas em SQLite.
- Layout responsivo e avisos de convivência segura.

## Segurança e limitações
- Mentoria e colaboração são solicitações internas. Não há sistema de mensagens privadas, verificação de mentoras ou compartilhamento de contato.
- Denúncias exigem ação humana de moderadores autorizados; não há moderação automática garantida.
- Perfil na busca exige opt-in. Conteúdo publicado no feed segue visível a outras pessoas da comunidade, sujeito a bloqueios e moderação.
- Os testes de sintaxe Python e JavaScript foram executados; o SQL novo foi validado em uma cópia do banco. Os testes de ponta a ponta no navegador ainda são necessários.

## Testes recomendados
1. Criar duas contas de teste, uma com perfil visível e outra privado.
2. Verificar que a conta privada não aparece na descoberta.
3. Enviar e aceitar/recusar convites, confirmar notificações.
4. Bloquear e desbloquear, confirmar restrição de feed e convites.
5. Publicar, comentar, curtir, denunciar e moderar com conta autorizada.
6. Testar em tela de celular, e confirmar que a LIA local continua respondendo.
