"""Temporary mocks test plumbing only; no formal experiment outputs are retained."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments import invoke,classification,probability_row,summarize,performance,probability
from project import cases,read_case,REF,run
from types import SimpleNamespace

class Plumbing(unittest.TestCase):
    def test_reproducible_and_real_space_path(self):
        m,p=next(cases())
        with tempfile.TemporaryDirectory(prefix='actual input with spaces ') as d:
            target=Path(d)/'input with spaces.txt'
            run([REF,'generate',target,m['n'],m['seed'],m['data_type'],'none',m['element_range'][0]])
            self.assertEqual(target.read_bytes(),p.read_bytes())
            self.assertTrue(json.loads(run([REF,'check',target]))['accepted'])

    def test_protocol(self):
        good=dict(accepted=True,elapsed_ns=123,algorithm='freivalds',rounds=5,seed=7)
        def result(stdout,code=0):return subprocess.CompletedProcess([],code,stdout,'test diagnostic')
        with patch('experiments.subprocess.run',return_value=result(json.dumps(good)+'\n')) as call:
            r,total=invoke(Path('test double.exe'),Path('path with spaces/input.txt'),'freivalds',5,7)
            self.assertTrue(r['accepted']);self.assertGreaterEqual(total,0)
            self.assertIn(str(Path('path with spaces/input.txt')),call.call_args.args[0])
        bad=[result('{}'),result('bad'),result(json.dumps(good)+'\nextra'),result('',1),
             result(json.dumps(dict(good,accepted=1))),result(json.dumps(dict(good,elapsed_ns=-1))),
             result(json.dumps(dict(good,seed=8)))]
        for response in bad:
            with patch('experiments.subprocess.run',return_value=response):
                with self.assertRaises((ValueError,RuntimeError)):
                    invoke('mock','input','freivalds',5,7)
        with patch('experiments.subprocess.run',side_effect=subprocess.TimeoutExpired('mock',120)):
            with self.assertRaises(subprocess.TimeoutExpired):invoke('mock','input','exact',1,0)

    def test_classification(self):
        self.assertEqual(classification(True,'freivalds',False),'BUG_FALSE_REJECT')
        self.assertEqual(classification(False,'exact',True),'BUG_EXACT')
        self.assertEqual(classification(False,'freivalds',True),'MISS')
        self.assertEqual(probability_row(2,10000,2500)['observed_rate'],.25)
        self.assertEqual(probability_row(10,10000,0)['expected_misses'],10000/1024)

    def test_pipeline_mock_only(self):
        with tempfile.TemporaryDirectory(prefix='freivalds mock ') as d:
            out=Path(d);exe=out/'test double.exe';exe.write_bytes(b'mock only')
            provenance=out/'build.json';provenance.write_text(json.dumps(dict(compiler='mock',optimization='-O2',os='mock',machine='mock',command=['mock'])))
            args=SimpleNamespace(exe=exe,out=out,provenance=provenance,warmups=2,repeats=3,fixed_n=256,trials=8)
            seeds=[]
            def fake(exe,path,alg,k,seed):
                seeds.append(seed);return dict(accepted=True,elapsed_ns=100,algorithm=alg,rounds=k,seed=seed),200
            with patch('experiments.invoke',side_effect=fake):
                performance(args);seeds.clear();probability(args)
            self.assertEqual(len(seeds),40);self.assertEqual(len(set(seeds)),40)
            self.assertTrue((out/'timing_summary.csv').exists())
            self.assertTrue((out/'probability_raw.csv').exists())

    def test_corruption(self):
        m,p=next(cases())
        with tempfile.TemporaryDirectory() as d:
            corrupt=Path(d)/p.name;corrupt.write_bytes(p.read_bytes()+b'0\n')
            with self.assertRaises(AssertionError):read_case(m,corrupt)

if __name__=='__main__':
    print('TEST DOUBLES ONLY / 仅测试替身；临时统计和计时在测试后删除，不是实验结果。',flush=True)
    unittest.main()
