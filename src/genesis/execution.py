"""Coordinator-owned execution of a fixed data-only DSL in bounded subprocesses.

This is not an arbitrary-code sandbox. Python/source/plugin submissions are never
accepted here. Docker is required for a future arbitrary generated-code backend.
"""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from .common import canonical,bytes_hash
from .models import GraphTask,SolverProgram,Limits
from .graphs import check_witness


def _child():
    import resource
    request=json.loads(sys.stdin.buffer.read(8*1024*1024+1))
    if set(request)!={'task','program','limits','seed'}:raise ValueError('request shape')
    task=GraphTask.model_validate_json(canonical(request['task']))
    program=SolverProgram.model_validate_json(canonical(request['program']))
    limits=Limits.model_validate_json(canonical(request['limits']))
    if type(request['seed']) is not int:raise ValueError('seed')
    resource.setrlimit(resource.RLIMIT_AS,(limits.memory_mib*1048576,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(limits.cpu_seconds,limits.cpu_seconds+1))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    if hasattr(resource,'RLIMIT_NPROC'):resource.setrlimit(resource.RLIMIT_NPROC,(0,0))
    from .dsl import solve
    start=time.process_time_ns()
    result=solve(task,program,limits.queries,request['seed'])
    result['algorithm_cpu_ns']=time.process_time_ns()-start
    result['cpu_ns']=time.process_time_ns()
    result['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    sys.stdout.buffer.write(canonical(result))


def execute(task,program,limits,seed):
    # Inputs are strict models, not arbitrary commands or module names.
    if not isinstance(task,GraphTask) or not isinstance(program,SolverProgram) or not isinstance(limits,Limits):
        raise TypeError('typed execution input required')
    request={'task':task.model_dump(mode='json'),'program':program.model_dump(mode='json'),
             'limits':limits.model_dump(mode='json'),'seed':seed}
    package_root=str(Path(__file__).resolve().parents[1])
    env={'PATH':'/usr/bin:/bin','PYTHONPATH':package_root,'PYTHONHASHSEED':'0',
         'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'}
    if sys.pycache_prefix:env['PYTHONPYCACHEPREFIX']=sys.pycache_prefix  # site bytecode stays inert
    start=time.monotonic_ns();deadline=time.monotonic()+limits.wall_seconds
    p=subprocess.Popen([sys.executable,'-m','genesis.execution','--trusted-dsl-child'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        env=env,cwd='/',start_new_session=True,close_fds=True)
    # Trusted bounded request fits the pipe for normal graph limits; communication
    # below handles even maximum graph inputs without trusting candidate callbacks.
    data=canonical(request)
    buffers={'stdout':bytearray(),'stderr':bytearray()};sizes={'stdout':0,'stderr':0}
    sel=selectors.DefaultSelector();sent=0;status='SUCCESS'
    for name,pipe in (('stdout',p.stdout),('stderr',p.stderr)):
        os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,name)
    os.set_blocking(p.stdin.fileno(),False);sel.register(p.stdin,selectors.EVENT_WRITE,'stdin')
    try:
        while sel.get_map() or p.poll() is None:
            if time.monotonic()>=deadline:status='TIMEOUT';break
            for key,_ in sel.select(min(.05,max(0,deadline-time.monotonic()))):
                name=key.data
                if name=='stdin':
                    try:sent+=os.write(key.fd,data[sent:sent+8192])
                    except BrokenPipeError:sent=len(data)
                    if sent==len(data):sel.unregister(key.fileobj);p.stdin.close()
                    continue
                chunk=os.read(key.fd,65536)
                if not chunk:sel.unregister(key.fileobj);continue
                sizes[name]+=len(chunk)
                remaining=limits.output_bytes-len(buffers[name])
                buffers[name].extend(chunk[:max(0,remaining)])
                if sizes[name]>limits.output_bytes:status='OUTPUT_LIMIT';break
            if status!='SUCCESS':break
    finally:
        if status!='SUCCESS' or p.poll() is None:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        p.wait(timeout=5);sel.close()
        for pipe in (p.stdin,p.stdout,p.stderr):
            if not pipe.closed:pipe.close()
    if status=='SUCCESS' and p.returncode!=0:
        status=('CPU_LIMIT' if p.returncode==-signal.SIGXCPU else
                'RESOURCE_KILLED' if p.returncode==-signal.SIGKILL else 'EXECUTION_ERROR')
    receipt={'status':status,'exit_code':p.returncode,'wall_ns':time.monotonic_ns()-start,
             'cpu_ns':None,'peak_rss_bytes':None,'limits':limits.model_dump(mode='json'),
             'stdout':bytes(buffers['stdout']).decode(errors='replace'),
             'stderr':bytes(buffers['stderr']).decode(errors='replace'),
             'output_bytes_observed':sizes,'truncated':status=='OUTPUT_LIMIT',
             'runner_sha256':bytes_hash(Path(__file__).read_bytes()),
             'execution_mode':'FIXED_DATA_ONLY_DSL','arbitrary_code_sandbox':False}
    if status=='SUCCESS':
        try:
            result=json.loads(buffers['stdout'])
            checked=check_witness(task,result['selected'])
            if type(result['value']) is not int or result['value']!=checked['value']:
                raise ValueError('claimed value differs from witness')
            if type(result['queries']) is not int or not 0<=result['queries']<=limits.queries:
                raise ValueError('invalid trusted interpreter query receipt')
            for field in ('cpu_ns','peak_rss_bytes'):
                if type(result[field]) is not int or result[field]<0:raise ValueError('invalid metrology')
            receipt.update(result=result,check=checked,cpu_ns=result['cpu_ns'],peak_rss_bytes=result['peak_rss_bytes'])
        except (ValueError,KeyError,TypeError) as e:
            receipt.update(status='CHECKER_ERROR',reason=str(e))
    return receipt


if __name__=='__main__':
    if sys.argv[1:]!=['--trusted-dsl-child']:raise SystemExit('internal fixed DSL runner only')
    _child()
