#!/usr/bin/env python3
"""Prepare file://-compatible GSI data without reading logs or regenerating figures."""
import argparse,gzip,json
from pathlib import Path
from environments import canonical_environment, STORAGE_IDS

def prepare(root):
    local=root/'local';local.mkdir(exist_ok=True)
    index=json.loads((root/'index.json').read_text())
    index['environment']=canonical_environment(index['environment'])
    key=STORAGE_IDS[index['environment']]
    if key not in ('smna-fn','smna-fc'):raise ValueError('Ambiente inválido no índice')
    prefix='window.SMNA_GSI_LOCAL=window.SMNA_GSI_LOCAL||{};window.SMNA_GSI_LOCAL['+json.dumps(key)+']=window.SMNA_GSI_LOCAL['+json.dumps(key)+']||{cycles:{}};'
    target='window.SMNA_GSI_LOCAL['+json.dumps(key)+']'
    (local/'index.js').write_text(prefix+target+'.index='+json.dumps(index,ensure_ascii=False,separators=(',',':'))+';\n')
    count=0
    for s in index['cycles']:
        if s['state']!='parsed':continue
        c=s['cycle'];p=root/'cycles'/(c+'.json.gz')
        detail=json.loads(gzip.decompress(p.read_bytes())) if p.exists() else json.loads((root/'cycles'/(c+'.json')).read_text())
        figures=json.loads((root/'plots'/c/'figures.json').read_text())
        for f in figures:
            if not (root/'plots'/c/f.get('file',f.get('png',''))).is_file():raise FileNotFoundError(f)
        data=json.dumps({'detail':detail,'figures':figures},ensure_ascii=False,separators=(',',':'))
        (local/(c+'.js')).write_text(prefix+target+'.cycles['+json.dumps(c)+']='+data+';\n')
        count+=1
    print(f'{count} ciclos preparados para abertura direta; nenhuma figura regenerada.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);a=p.parse_args();prepare(a.data)
