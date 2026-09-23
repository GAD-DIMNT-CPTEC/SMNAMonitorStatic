"""Offline regression tests: isolation, content updates, failures and locking."""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import operational as op

NAME='model_2026092218.2026092303.log'
HEADER='''**(DumpOptions)** model TQ0299L064 runs from 18Z 22/09/2026 to 03Z 23/09/2026 with initial state from 18Z 22/09/2026
**(DumpOptions)** model executes 162 timesteps of length 200 seconds
'''

def lightweight_export(data,out,env):
    data['environment']=env;data['figures']=[]
    (out/'diagnostics.json').write_text(json.dumps(data))
    (out/'test.png').write_bytes(b'test product')

class OperationalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for env in op.ENVS:
            (self.root/env).mkdir();(self.root/env/NAME).write_text(HEADER+env)
        self.args=argparse.Namespace(output=self.root/'public',cache=self.root/'cache',smna_finpe=str(self.root/'smna-finpe'),smna_fncep=str(self.root/'smna-fncep'),limit=0,timeout=5)
    def tearDown(self): self.tmp.cleanup()
    def run_update(self):
        with patch.object(op,'export',side_effect=lightweight_export),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):return op.run(self.args)
    def catalog(self):return json.loads((self.args.output/'index.json').read_text())
    def test_isolation_cache_and_changed_content(self):
        self.assertEqual(self.run_update(),0); first=self.catalog()
        a=first['environments']['smna-finpe']['runs'][0];b=first['environments']['smna-fncep']['runs'][0]
        self.assertNotEqual(a['path'],b['path']);self.assertNotEqual(a['sha256'],b['sha256'])
        self.assertEqual(self.run_update(),0);self.assertEqual(self.catalog()['environments']['smna-finpe']['runs'][0]['id'],a['id'])
        with (self.root/'smna-finpe'/NAME).open('a') as f:f.write('\nMODEL EXECUTION ENDS NORMALY')
        self.assertEqual(self.run_update(),0);new=self.catalog()['environments']['smna-finpe']['runs'][0]
        self.assertNotEqual(new['id'],a['id']);self.assertTrue(new['normal_end']);self.assertTrue((self.args.output/a['path']).exists())
    def test_invalid_replacement_preserves_previous(self):
        self.run_update();old=self.catalog()['environments']['smna-finpe']['runs'][0]['id']
        (self.root/'smna-finpe'/NAME).write_text('truncated log')
        self.assertEqual(self.run_update(),2);env=self.catalog()['environments']['smna-finpe']
        self.assertTrue(env['errors']);self.assertEqual(env['runs'][0]['id'],old);self.assertIn('error',env['runs'][0])
    def test_missing_product_is_rebuilt(self):
        self.run_update();old=self.catalog()['environments']['smna-finpe']['runs'][0]
        (self.args.output/old['path']/'test.png').unlink()
        self.assertEqual(self.run_update(),0);new=self.catalog()['environments']['smna-finpe']['runs'][0]
        self.assertNotEqual(old['id'],new['id']);self.assertTrue((self.args.output/new['path']/'test.png').exists())
    def test_filename_dates_and_incomplete_header(self):
        d=op.parse(self.root/'smna-finpe'/NAME);self.assertFalse(d['normal_end']);self.assertEqual(d['profiles'],[])
        (self.root/'smna-finpe'/NAME).write_text(HEADER.replace('18Z 22/09','12Z 22/09'))
        self.assertEqual(self.run_update(),2);self.assertEqual(self.catalog()['environments']['smna-finpe']['runs'],[])
    def test_concurrent_lock(self):
        self.args.output.mkdir()
        with (self.args.output/'.update.lock').open('a') as lock:
            op.fcntl.flock(lock,op.fcntl.LOCK_EX|op.fcntl.LOCK_NB)
            self.assertEqual(self.run_update(),3)

if __name__=='__main__':unittest.main()
