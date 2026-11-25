"""Interpretador didático limitado: não usa exec/eval, não acessa arquivos ou rede."""
import ast
import operator


def run(source):
    if len(source)>12000: raise ValueError('Código muito longo.')
    tree=ast.parse(source)
    if sum(1 for _ in ast.walk(tree))>700: raise ValueError('Exercício muito complexo.')
    env={}; output=[]; steps=0
    def tick():
        nonlocal steps
        steps+=1
        if steps>1500: raise ValueError('Limite de operações atingido.')
    def bound(v):
        if type(v) is int and abs(v)>10**15: raise ValueError('Número muito grande.')
        if isinstance(v,(str,list,tuple)) and len(v)>2000: raise ValueError('Valor muito grande.')
        return v
    def expr(n):
        tick()
        if isinstance(n,ast.Constant) and type(n.value) in (str,int,float,bool,type(None)): return bound(n.value)
        if isinstance(n,ast.Name) and n.id in env: return env[n.id]
        if isinstance(n,(ast.List,ast.Tuple)): return bound([expr(x) for x in n.elts])
        if isinstance(n,ast.UnaryOp):
            a=expr(n.operand)
            if isinstance(n.op,ast.Not): return not a
            if type(a) in (int,float) and isinstance(n.op,(ast.USub,ast.UAdd)): return bound(-a if isinstance(n.op,ast.USub) else a)
        if isinstance(n,ast.BinOp):
            a,b=expr(n.left),expr(n.right)
            if isinstance(n.op,ast.Add) and type(a) is type(b) and type(a) in (str,list): return bound(a+b)
            if type(a) in (int,float) and type(b) in (int,float):
                ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
                if type(n.op) in ops:return bound(ops[type(n.op)](a,b))
        if isinstance(n,ast.Compare) and len(n.ops)==1:
            a,b=expr(n.left),expr(n.comparators[0]);ops={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge}
            if type(n.ops[0]) in ops:return ops[type(n.ops[0])](a,b)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and not n.keywords:
            args=[expr(x) for x in n.args]
            if n.func.id=='print':
                output.append(' '.join(str(x) for x in args)[:2000]);return None
            if n.func.id=='len' and len(args)==1:return len(args[0])
            if n.func.id=='range' and 1<=len(args)<=3 and all(type(x) is int for x in args):
                r=range(*args)
                if len(r)>300:raise ValueError('Laço muito longo.')
                return list(r)
        raise ValueError('Recurso não disponível no executor didático. Use Verificar para validar a sintaxe completa.')
    def block(nodes):
        for n in nodes:
            tick()
            if isinstance(n,ast.Expr):expr(n.value)
            elif isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):env[n.targets[0].id]=expr(n.value)
            elif isinstance(n,ast.If):block(n.body if expr(n.test) else n.orelse)
            elif isinstance(n,ast.For) and isinstance(n.target,ast.Name) and not n.orelse:
                items=expr(n.iter)
                if not isinstance(items,(list,str)) or len(items)>300:raise ValueError('Laço muito longo.')
                for item in items:tick();env[n.target.id]=item;block(n.body)
            elif isinstance(n,ast.Pass):pass
            else:raise ValueError('Recurso não disponível no executor didático. Use Verificar para validar a sintaxe completa.')
    block(tree.body)
    return '\n'.join(output)[:12000]
