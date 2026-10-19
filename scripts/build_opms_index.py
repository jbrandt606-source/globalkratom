#!/usr/bin/env python3
"""Build a static, page-level full-text index of opms/pdfs/*.pdf.
Requires PyMuPDF. Optional Tesseract for image-only pages.
Preserves original PDFs; output goes to opms/search-data/.
"""
import argparse, hashlib, json, re, shutil, subprocess, sys
from collections import defaultdict
from pathlib import Path
import fitz

GROUPS={'132':'Corporate structure and finances','217':'Florida fatality study','237':'Pharmacology and expert testimony','239':'Product warnings','241':'FDA compliance','249':'Boyer toxicology dispute','253':'Comparative fault and labels','267':'Defense summary judgment','313':'Pretrial evidence','315':'Plaintiff summary judgment'}

def compact(s):
    return re.sub(r'\s+', ' ', s).strip()

def ocr_page(page, lang):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'page.png'
        pix=page.get_pixmap(matrix=fitz.Matrix(1.7,1.7), alpha=False, colorspace=fitz.csGRAY)
        pix.save(str(path))
        p=subprocess.run(['tesseract',str(path),'stdout','-l',lang],capture_output=True,text=True,timeout=100)
        if p.returncode: raise RuntimeError(p.stderr.strip()[:200])
        return compact(p.stdout)

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',default='.');a.add_argument('--ocr',choices=['auto','off'],default='auto');a.add_argument('--lang',default='eng');args=a.parse_args()
    root=Path(args.root).resolve(); pdfdir=root/'opms/pdfs'; out=root/'opms/search-data'; cache=out/'docs'
    if not pdfdir.is_dir(): sys.exit(f'Missing PDF folder: {pdfdir}')
    files=sorted(pdfdir.rglob('*.pdf'),key=lambda p:p.name.lower())
    if not files: sys.exit('No PDFs found. Index not generated.')
    cache.mkdir(parents=True,exist_ok=True)
    has_ocr=shutil.which('tesseract') is not None
    docs=[]; groups=defaultdict(list); stats={'documents':0,'pages':0,'ocr_pages':0,'unsearchable_pages':0,'failed_documents':0}
    active=set()
    for n,path in enumerate(files,1):
        rel=path.relative_to(root).as_posix(); ident=hashlib.sha1(rel.encode()).hexdigest()[:16]; dest=cache/(ident+'.json');active.add(dest.name)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        record=None
        if dest.exists():
            try:
                candidate=json.loads(dest.read_text('utf8'))
                if candidate.get('sha256')==digest and (args.ocr=='off' or candidate.get('ocr_enabled')==(args.ocr=='auto' and has_ocr)):
                    record=candidate
            except (ValueError,OSError):pass
        if record is None:
            pages=[]; errors=[]
            try:
                with fitz.open(path) as pdf:
                    for i in range(len(pdf)):
                        page=pdf[i]; txt=compact(page.get_text(sort=True)); mode='text' if len(txt)>=25 else 'empty'
                        if mode=='empty' and args.ocr=='auto' and has_ocr:
                            try:
                                scanned=ocr_page(page,args.lang)
                                if len(scanned)>len(txt): txt=scanned;mode='ocr' if txt else 'empty'
                            except Exception as exc:errors.append(f'page {i+1}: {str(exc)[:120]}')
                        pages.append({'n':i+1,'t':txt,'mode':mode})
            except Exception as exc:
                print(f'ERROR {rel}: {exc}',file=sys.stderr);stats['failed_documents']+=1;continue
            record={'id':ident,'path':rel,'sha256':digest,'ocr_enabled':args.ocr=='auto' and has_ocr,'pages':pages,'errors':errors}
            dest.write_text(json.dumps(record,ensure_ascii=False,separators=(',',':')),'utf8')
        prefix=re.match(r'^(\d+)',path.stem); group=prefix.group(1) if prefix else 'other'
        meta={'id':ident,'name':path.name,'path':'/'+rel,'group':group,'category':GROUPS.get(group,'Other court records'),'pages':len(record['pages']),'ocr':sum(p['mode']=='ocr' for p in record['pages']),'unsearchable':sum(not p['t'] for p in record['pages'])}
        docs.append(meta);groups[group].append(meta)
        stats['pages']+=meta['pages'];stats['ocr_pages']+=meta['ocr'];stats['unsearchable_pages']+=meta['unsearchable']
        print(f'[{n}/{len(files)}] {path.name}: {meta["pages"]} pages, {meta["ocr"]} OCR, {meta["unsearchable"]} blank',flush=True)
    for stale in cache.glob('*.json'):
        if stale.name not in active:stale.unlink()
    # Shard by size; each shard contains page text and metadata for self-contained searching.
    for old in out.glob('chunk-*.json'):old.unlink()
    chunk=[];size=0;chunks=[]
    def flush():
        nonlocal chunk,size
        if not chunk:return
        filename=f'chunk-{len(chunks):04d}.json'
        (out/filename).write_text(json.dumps(chunk,ensure_ascii=False,separators=(',',':')),'utf8')
        chunks.append(filename);chunk=[];size=0
    for doc in docs:
        record=json.loads((cache/(doc['id']+'.json')).read_text('utf8'))
        for page in record['pages']:
            if not page['t']:continue
            item={'d':doc['id'],'p':page['n'],'t':page['t']}
            estimated=len(page['t'].encode('utf8'))+80
            if size+estimated>650_000:flush()
            chunk.append(item);size+=estimated
    flush();stats['documents']=len(docs)
    manifest={'version':1,'stats':stats,'documents':docs,'chunks':chunks,'groups':GROUPS}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),'utf8')
    print('INDEX COMPLETE',json.dumps(stats),f'{len(chunks)} shards',flush=True)
    if stats['failed_documents']:sys.exit('Some PDFs failed; see log')
if __name__=='__main__':main()
