import itertools,json,sqlite3,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import assessment_engine as a

class AssessmentTests(unittest.TestCase):
 def test_bank_is_specific_and_complete(self):
  courses=json.loads((ROOT/'curriculo.json').read_text())['courses']; all_lessons=[l for c in courses for l in c['lessons']]
  self.assertEqual(len(all_lessons),702);self.assertEqual(len({l['question'] for l in all_lessons}),702)
  modules=0
  for c in courses:
   for name,group in itertools.groupby(c['lessons'],lambda l:l['module']):
    ls=list(group);pr=a.practice_for(c['id'],name,ls);modules+=1
    self.assertTrue(pr['task'] and pr['question'] and pr['accepted']);self.assertEqual(len(a.quiz_items(ls)),len(ls))
    keys={l['id']:l['correct'] for l in ls}
    good=a.grade_module(ls,pr,keys,pr['accepted'][0]);self.assertEqual(good['score'],100);self.assertTrue(good['passed'])
    wrong={l['id']:(l['correct']+1)%len(l['options']) for l in ls}
    self.assertFalse(a.grade_module(ls,pr,wrong,pr['accepted'][0])['passed'])
    self.assertTrue(a.grade_module(ls,pr,keys,'')['passed'])
    self.assertFalse(good['has_applied'])
  self.assertEqual(modules,86)
 def test_threshold_and_validity(self):
  ls=[{'id':str(i),'title':str(i),'question':'Q','options':['A','B'],'correct':0} for i in range(4)]
  pr={'question':'Q','accepted':['42']}
  self.assertTrue(a.grade_module(ls,pr,{'0':0,'1':0,'2':0,'3':1},'')['passed'])
  self.assertFalse(a.grade_module(ls,pr,{'0':0,'1':0,'2':1,'3':1},'42')['passed'])
  with self.assertRaises(ValueError):a.grade_module(ls,pr,{'0':0},'42')
  with self.assertRaises(ValueError):a.grade_module(ls,pr,{'0':True,'1':0,'2':0,'3':0},'42')
 def test_delivery(self):
  self.assertEqual(a.validate_delivery({'solution':'print(1)'}),('print(1)',''))
  with self.assertRaises(ValueError):a.validate_delivery({'solution':'','tests':'aaa'})
  self.assertEqual(a.validate_delivery({'solution':'  def soma(a, b): return a + b ','tests':' Entrada 2, 3; saída 5. '}),('def soma(a, b): return a + b','Entrada 2, 3; saída 5.'))
 def test_database(self):
  with sqlite3.connect(ROOT/'conectas.db') as conn:
   self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
   lessons=[json.loads(x[0]) for x in conn.execute('SELECT payload FROM catalog_lessons')]
   self.assertEqual(sum(l.get('question_revision')==2 for l in lessons),702)
if __name__=='__main__':unittest.main()
