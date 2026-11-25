# PASSO 11 — Perfil personalizado

- Abas: Dados pessoais, Minha evolução, Meu Portfólio e Configurações.
- Foto: upload de JPG, PNG ou WebP com validação e redimensionamento Pillow; URL HTTPS também preservada.
- Nome, biografia, objetivos, habilidades, linguagens e ocupação: persistência na tabela users.
- Cursos, gráficos, certificados e conquistas: registros existentes, sem dados inventados.
- Portfólio: reutiliza os recursos do PASSO 9 e configurações públicas opt-in.
- Senha: verificação da senha atual e armazenamento do hash seguro.
- Notificações: preferências armazenadas na nova tabela profile_notifications. Essas preferências são salvas, mas não substituem a lógica de envio de cada categoria de notificação.
- LIA local e recursos dos passos anteriores preservados.

## Testar
Instale `pip install -r requirements.txt`; execute `python app.py`. Entre, teste cada aba, envie foto, atualize perfil, altere senha, verifique privacidade e histórico. Testes funcionais completos devem ser realizados no Codespaces.
