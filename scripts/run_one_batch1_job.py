#!/usr/bin/env python3
import argparse, importlib.util, json, pathlib
ap=argparse.ArgumentParser(); ap.add_argument('arm'); ap.add_argument('world'); ap.add_argument('out')
a=ap.parse_args()
p=pathlib.Path(__file__).with_name('genesis_batch1_repair.py')
spec=importlib.util.spec_from_file_location('b1',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
th=m.GRIDS['U'][0] if a.arm=='U' else None
r=m.run_arm(a.arm,a.world,th)
pathlib.Path(a.out).write_text(json.dumps(r,indent=1,default=str))
print(json.dumps({'world':r['world'],'arm':r['arm'],'sealed_solved':r['sealed_solved'],'sealed_n':r['sealed_n'],'admitted':len(r['admitted']),'spent':r['spent'],'seconds':r['seconds']}))
