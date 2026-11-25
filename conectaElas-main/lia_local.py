"""Tutor local educativo: não executa códigos e não utiliza serviços externos."""
import ast
import json
import re

def respond(question, code='', language='', mode='explain', level='iniciante', context=''):
    q = question.lower()
    language = language.lower()
    issues = []
    tips = []
    if code.strip():
        if language == 'python':
            try:
                ast.parse(code)
                tips.append('A análise sintática do Python não encontrou erros. Isso não garante que a lógica esteja correta.')
            except SyntaxError as e:
                issues.append(f'Linha {e.lineno}: {e.msg}. Verifique a indentação, os dois-pontos, parênteses e aspas.')
        elif language == 'json':
            try:
                json.loads(code)
                tips.append('O JSON é válido sintaticamente.')
            except json.JSONDecodeError as e:
                issues.append(f'Linha {e.lineno}, coluna {e.colno}: {e.msg}.')
        elif language in ('javascript', 'java', 'css'):
            if code.count('{') != code.count('}'):
                issues.append('A quantidade de chaves de abertura e fechamento é diferente.')
            if code.count('(') != code.count(')'):
                issues.append('A quantidade de parênteses de abertura e fechamento é diferente.')
            tips.append('Esta é uma verificação básica, não um compilador ou interpretador.')
        elif language == 'html':
            if not re.search(r'<[a-z][^>]*>', code, re.I):
                issues.append('Não encontrei uma tag HTML reconhecível.')
            tips.append('Confira a hierarquia, as tags de fechamento e os atributos.')
        elif language == 'sql':
            if not re.search(r'\b(select|insert|update|delete|create|alter)\b', code, re.I):
                issues.append('Não identifiquei um comando SQL comum.')
            tips.append('Verifique nomes de tabelas, condições WHERE e parâmetros; nenhuma consulta foi executada.')
    if mode == 'lines' and code.strip():
        rows = [f'Linha {i}: {line.strip()[:140]} — '+('linha vazia ou de espaçamento' if not line.strip() else 'identifique o comando, seus argumentos e seu efeito no programa') for i,line in enumerate(code.splitlines()[:25],1)]
        return 'Leitura guiada (não é uma interpretação automática completa):\n'+'\n'.join(rows)+'\n\nExperimente explicar com suas palavras o que cada linha faz.'
    if issues:
        return 'Encontrei possíveis problemas:\n'+'\n'.join('• '+i for i in issues)+'\n\nCorrija um ponto por vez e teste no ambiente apropriado.'
    if code.strip():
        return 'Análise local do código:\n'+'\n'.join('• '+x for x in tips)+'\n\nPara investigar a lógica, descreva o resultado esperado e compare com o resultado real. A LIA local não executou seu código.'
    topics = [
      (('variável','variavel'), 'Uma variável guarda um valor para reutilizar. Exemplo em Python: `idade = 16`. O valor pode mudar durante o programa.'),
      (('for','laço','laco','repetição','repeticao'), 'O laço `for` repete uma ação para cada item. Exemplo: `for numero in range(3): print(numero)` percorre 0, 1 e 2.'),
      (('lista','array'), 'Uma lista armazena vários itens em ordem. Exemplo: `cores = ["roxo", "azul"]`; `cores[0]` acessa o primeiro item.'),
      (('função','funcao'), 'Uma função reúne instruções reutilizáveis. Exemplo: `def dobro(x): return x * 2`.'),
      (('html',), 'HTML organiza o conteúdo de uma página usando elementos como `<h1>`, `<p>` e `<button>`.'),
      (('css',), 'CSS define a aparência da página. Exemplo: `h1 { color: purple; }` muda a cor dos títulos.'),
      (('javascript','js'), 'JavaScript permite interatividade no navegador, como responder a cliques e atualizar elementos da página.'),
      (('sql','banco de dados'), 'SQL permite consultar e modificar dados. Exemplo: `SELECT nome FROM alunos;` consulta a coluna nome.'),
      (('python',), 'Python é uma linguagem de programação com sintaxe legível. Comece com variáveis, condições, laços e funções.'),
    ]
    answer = next((a for keys,a in topics if any(k in q for k in keys)), None)
    if not answer:
        answer = 'Posso ajudar com Python, HTML, CSS, JavaScript, SQL e lógica. Diga qual conceito você está estudando ou cole um trecho de código para uma verificação básica.'
    if mode == 'hint':
        return 'Pista: qual é a entrada, qual resultado você espera e qual pequeno passo pode testar primeiro?\n\n'+answer
    if level == 'avancado':
        return answer+'\n\nConsidere também testes, tratamento de erros e legibilidade.'
    if level == 'iniciante':
        return answer+'\n\nQuer tentar um exemplo simples com esse conceito?'
    return answer

# Revisão estática complementar e navegação da plataforma, sem executar código.
_base_respond = respond

def respond(question, code='', language='', mode='explain', level='iniciante', context=''):
    q=question.lower().strip()
    if not code.strip() and q.rstrip('!?.') in ('oi','olá','ola','bom dia','boa tarde','boa noite','tudo bem','oi lia','olá lia'):
        return 'Olá! Sou a LIA, assistente do ConectaElas. Posso ajudar você a encontrar um curso, organizar estudos, revisar código ou entender o site. O que você gostaria de fazer?'
    if not code.strip():
        routes=[(('candidatar','candidatura','vaga','salário','salario'), 'Abra Encontrar trabalhos (/oportunidades). Escolha uma vaga, confira requisitos e salário, depois clique em Candidatar-me. O andamento aparece em Minhas candidaturas. Contratantes usam Área da empresa e Candidaturas recebidas.'), (('cronograma','organizar estudos','plano de estudos','minhas dificuldades'), 'Abra Trilha personalizada (/trilha-personalizada), selecione objetivo, nível e horas semanais. Após gerar o plano, veja Revisão das suas dificuldades e o cronograma semanal. As recomendações usam suas tentativas registradas.'), (('trilha','personalizada'), 'Abra Trilha personalizada (/trilha-personalizada), selecione um objetivo e gere seu caminho. Os círculos roxos indicam etapas disponíveis e concluídas; as cinzas são etapas futuras.'), (('certificado',), 'Abra Certificados (/certificados). Conclua aulas e avaliações dos módulos para receber o PDF automaticamente.'), (('comunidade','publicação','comentário'), 'Abra Comunidade (/comunidade), escolha um grupo e publique sua dúvida. Use Comentar ou Responder para conversar sem compartilhar dados pessoais.'), (('laboratório','laboratorio','editor','revisar código'), 'Abra Laboratório (/laboratorio), selecione a linguagem, cole seu código e use Corrigir com LIA. A revisão local não executa o código.'), (('perfil','portfólio','portfolio'), 'Abra Meu perfil (/perfil) para editar suas informações, acompanhar desempenho e gerenciar o portfólio.'), (('abrir curso','encontrar curso','iniciar curso','onde ficam os cursos','como acessar a aula'), 'Abra Cursos (/cursos), filtre por área e nível e selecione um curso. As aulas estão organizadas em módulos. Use os exercícios e a avaliação para avançar.')]
        for keys,answer in routes:
            if any(k in q for k in keys):return answer
    result=_base_respond(question,code,language,mode,level,context)
    notes=[]
    if code.strip() and language.lower()=='python':
        try:
            tree=ast.parse(code)
            for n in ast.walk(tree):
                if isinstance(n,ast.ExceptHandler) and n.type is None:notes.append(f'Linha {n.lineno}: prefira capturar uma exceção específica em vez de except genérico.')
                if isinstance(n,ast.Compare) and any(isinstance(op,(ast.Is,ast.IsNot)) for op in n.ops) and any(isinstance(x,ast.Constant) and type(x.value) in (int,str,float) for x in n.comparators):notes.append(f'Linha {n.lineno}: use == ou != para comparar valores; is verifica identidade.')
                if isinstance(n,ast.FunctionDef) and any(isinstance(x,(ast.List,ast.Dict,ast.Set)) for x in n.args.defaults):notes.append(f'Linha {n.lineno}: argumento padrão mutável pode compartilhar estado entre chamadas; considere None e inicialização dentro da função.')
                if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Div,ast.FloorDiv,ast.Mod)) and isinstance(n.right,ast.Constant) and n.right.value==0:notes.append(f'Linha {n.lineno}: divisão por zero; valide o divisor antes da operação.')
        except (SyntaxError,RecursionError):pass
    elif code.strip() and language.lower()=='html':
        if re.search(r'<img\b(?![^>]*\balt\s*=)[^>]*>',code,re.I):notes.append('Há imagem sem atributo alt; descreva a função da imagem ou use alt vazio se for decorativa.')
    elif code.strip() and language.lower()=='sql':
        if re.search(r'\b(?:UPDATE|DELETE\s+FROM)\b[^;]*(?:;|$)',code,re.I) and not re.search(r'\bWHERE\b',code,re.I):notes.append('UPDATE ou DELETE sem WHERE pode afetar todas as linhas. Confira a intenção e use uma consulta de verificação.')
    if code.strip():
        if notes:result+='\n\nRevisão complementar (verificação estática):\n'+'\n'.join('• '+n for n in notes[:12])
        result+='\n\nChecklist: confirme o resultado esperado, teste entradas vazias e limites, e revise nomes e tratamento de erros. Não compartilhe senhas ou chaves.'
    return result
