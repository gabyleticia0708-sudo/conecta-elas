"""Avaliações educacionais. Não executa código enviado pelas alunas."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

BANK = Path(__file__).resolve().parent / 'question_bank'
REVISIONS = json.loads((BANK / 'revision.json').read_text(encoding='utf-8'))
PRACTICES = json.loads((BANK / 'module_practice.json').read_text(encoding='utf-8'))
PASS_PERCENT = 70
QUIZ_FIELDS = ('question', 'options', 'correct', 'quizExplanation')


def upgrade_legacy_questions(conn):
    """Migra somente os enunciados originais; mantém alterações feitas por administradoras."""
    for row in conn.execute('SELECT lesson_id,payload FROM catalog_lessons').fetchall():
        revision = REVISIONS.get(row['lesson_id'])
        if not revision:
            continue
        lesson = json.loads(row['payload'])
        old = {key: lesson.get(key) for key in QUIZ_FIELDS}
        digest = hashlib.sha256(json.dumps(old, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if digest == revision['old_hash']:
            lesson.update(revision['fields'])
            conn.execute('UPDATE catalog_lessons SET payload=? WHERE lesson_id=?',
                         (json.dumps(lesson, ensure_ascii=False), row['lesson_id']))


def practice_for(course_id, module, lessons):
    entry = PRACTICES.get(course_id, {}).get(module)
    if entry:
        return entry
    # Novos módulos criados pelo painel continuam suportados.
    titles = ', '.join(str(l.get('title', '')) for l in lessons)
    return {'task': 'Crie uma solução que utilize os conteúdos do módulo: ' + titles +
            '. Inclua um caso normal, um limite e uma entrada inválida. Explique como verificou cada resultado.',
            'question': '', 'accepted': []}


def quiz_items(lessons):
    return [l for l in lessons if isinstance(l.get('options'), list) and len(l['options']) >= 2
            and type(l.get('correct')) is int and 0 <= l['correct'] < len(l['options']) and l.get('question')]


def normalize_short(value):
    # Aceita variações triviais de espaços, capitalização e acentos.
    text = unicodedata.normalize('NFKD', str(value).strip().casefold())
    return re.sub(r'\s+', ' ', ''.join(c for c in text if not unicodedata.combining(c)))


def grade_module(lessons, practice, answers, applied):
    items = quiz_items(lessons)
    if not items:
        raise ValueError('Este módulo ainda não possui questões válidas. Solicite revisão do catálogo.')
    if not isinstance(answers, dict) or set(answers) != {l['id'] for l in items}:
        raise ValueError('Responda a todas as questões da avaliação.')
    for l in items:
        a = answers[l['id']]
        if type(a) is not int or not 0 <= a < len(l['options']):
            raise ValueError('Selecione uma alternativa válida em todas as questões.')
    results = [{'id': l['id'], 'title': l['title'], 'correct': answers[l['id']] == l['correct']} for l in items]
    total = len(results)
    correct = sum(r['correct'] for r in results)
    return {'total': total, 'hits': correct, 'score': round(100*correct/total, 1),
            'passed': correct*100 >= PASS_PERCENT*total,
            'applied_correct': True, 'has_applied': False, 'results': results}


def validate_delivery(payload):
    if not isinstance(payload, dict):
        raise ValueError('Informe a solução e os testes.')
    solution, tests = payload.get('solution'), payload.get('tests', '')
    if not isinstance(solution, str) or not 1 <= len(solution.strip()) <= 12000:
        raise ValueError('Escreva ou cole sua solução (1 a 12.000 caracteres).')
    if not isinstance(tests, str) or len(tests.strip()) > 4000:
        raise ValueError('As anotações opcionais devem ter até 4.000 caracteres.')
    return solution.strip(), tests.strip()
