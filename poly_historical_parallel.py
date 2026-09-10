import subprocess, sys, time, json, pathlib, concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parent; PY=r'D:\APP\Anaconda\python.exe'; WORK=ROOT/'layer2_results'/'poly_historical_workers'; WORK.mkdir(parents=True,exist_ok=True)
def run(i):
 p=subprocess.run([PY,str(ROOT/'poly_historical_worker.py'),'--index',str(i)],cwd=ROOT,capture_output=True,text=True)
 return i,p.returncode,p.stdout[-1000:],p.stderr[-1000:]
def main():
 t=time.time(); done=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  fut={ex.submit(run,i):i for i in range(1,351)}
  for f in concurrent.futures.as_completed(fut):
   i,rc,out,err=f.result(); done+=1; print(f'[{done}/350] idx={i} rc={rc} {out.strip()}',flush=True)
   if rc!=0: print(err,flush=True)
 print('ALL_DONE',done,'elapsed',time.time()-t)
if __name__=='__main__': main()
