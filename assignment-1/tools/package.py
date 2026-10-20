"""Package only this project's deliverables; preserve existing unrelated files."""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from project import ROOT,save

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    dest=ROOT
    files=[ROOT/'README.md',ROOT/'.gitignore']
    for folder in ['src','docs','tools','build','data','results']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    hashes={}
    for source in sorted(files):
        name=source.relative_to(ROOT).as_posix()
        hashes[name]=sha(source)
    save(dest/'PACKAGE_MANIFEST.json',dict(algorithm='SHA-256',files=hashes))
    archive=dest/'freivalds.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in [*hashes,'PACKAGE_MANIFEST.json']:z.write(dest/name,name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in hashes.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
        assert z.read('PACKAGE_MANIFEST.json')==(dest/'PACKAGE_MANIFEST.json').read_bytes()
    records=[]
    for command in [['tools/project.py','check'],['tools/selftest.py']]:
        p=subprocess.run([sys.executable,'-B',*command],cwd=dest,capture_output=True,
             text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
        records.append(dict(command=['python','-B',*command],exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
    # The verifier itself stays outside the archive to avoid a self-referential hash.
    save(dest/'PACKAGE_VERIFY.json',dict(status='PASS' if all(r['exit_code']==0 for r in records) else 'FAIL',
         packaged_files=len(hashes),files_zip_hashes_equal=True,archive_sha256=sha(archive),
         checks=records))
    if any(r['exit_code'] for r in records):raise RuntimeError('packaged check failed')
    print(json.dumps(dict(directory=str(dest),files=len(hashes),zip_bytes=archive.stat().st_size,
                         hash_check='PASS',packaged_checks='PASS'),ensure_ascii=False))

if __name__=='__main__':main()
