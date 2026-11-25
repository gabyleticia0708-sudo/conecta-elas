# Login, troca de conta e e-mail

A atualização invalida sessões antigas sem identificador no banco. Entre novamente após publicar. Sair da conta revoga a sessão atual e redireciona para /entrar?switch=1. O cadastro continua disponível sem serviço de e-mail; o endereço fica marcado como não confirmado até a pessoa confirmar o link. A confirmação não é obrigatória para entrar, para preservar contas anteriores e testes locais.

## Render
Configure nas variáveis de ambiente do serviço:
- SECRET_KEY: segredo longo e privado, estável entre deploys.
- COOKIE_SECURE: 1 (HTTPS); em localhost HTTP, use 0.
- RESEND_API_KEY: chave privada de envio de e-mail do Resend.
- MAIL_FROM: remetente autorizado pelo serviço, como ConectaElas <contato@seu-dominio.example> (substitua pelo endereço real autorizado).
- PUBLIC_BASE_URL: endereço HTTPS real do site, sem caminho final.

Resend usa HTTPS; não requer SMTP no Render. O serviço possui modalidade gratuita com limites; o envio geral requer domínio verificado. O remetente de testes pode ser limitado ao próprio endereço da conta. Configure com o responsável pelo projeto e respeite os termos do serviço. Nunca publique a chave. Sem configuração, o site continua permitindo login/cadastro, mas informa que recuperação/reenviar confirmação não está disponível. A confirmação de endereço comprova acesso à caixa de entrada; a validação de formato não comprova existência.

## Testes manuais
1. Entre na conta A, saia pelo menu, entre na conta B ou crie uma conta C.
2. Clique Esqueci minha senha, informe o endereço cadastrado, abra o link recebido e escolha nova senha. A senha antiga não deve funcionar. O link é descartável e expira em 30 minutos.
3. Crie conta com e-mail real, receba a mensagem de confirmação e confirme pelo botão do link. É possível reenviar no menu da conta. O link expira em 24 horas.
4. A recuperação não revela publicamente quais endereços estão cadastrados.

SQLite continua sujeito à perda de dados no armazenamento efêmero do Render gratuito. Migração para armazenamento persistente permanece pendente.
