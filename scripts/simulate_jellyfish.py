"""Simulate and cache native cloth/hair outputs; record measurable motion checks."""
from pathlib import Path
import argparse,json,math,time
import hou

def main():
    p=argparse.ArgumentParser();p.add_argument('hip');p.add_argument('--end',type=int,default=180);args=p.parse_args()
    path=Path(args.hip).resolve();hou.hipFile.load(str(path),suppress_save_prompt=True)
    a=hou.node('/obj/jellyfish/jellyfish_generator');a.parm('use_cache').set(0)
    folder=path.parent/'cache';folder.mkdir(exist_ok=True)
    kinds=[('arms','ARMS_VELLUM_SOLVER','point_deform_arm_targets','arm_roots'),
           ('tentacles','TENTACLES_VELLUM_SOLVER','point_deform_tentacle_targets','tentacle_roots')]
    report={'houdini':hou.applicationVersionString(),'frame_range':[1,args.end],'checks':[]}
    t=time.time()
    for frame in range(1,args.end+1):
        hou.setFrame(frame)
        for label,solver,target,group in kinds:
            n=a.node(solver);geo=n.geometry()
            if n.errors():raise RuntimeError((n.path(),n.errors()))
            if not geo.points():raise RuntimeError('Empty '+label)
            pos=[pt.position() for pt in geo.points()]
            assert all(math.isfinite(c) for q in pos for c in q), (label,frame)
            temporary=folder/f'.{label}.{frame:04d}.tmp.bgeo.sc'
            geo.saveToFile(str(temporary))
            temporary.replace(folder/f'{label}.{frame:04d}.bgeo.sc')
            if frame in (1,12,36,37,60,96,120,180,args.end):
                goal=a.node(target).geometry()
                roots=geo.findPointGroup(group).points()
                root_error=max((pt.position()-goal.point(pt.number()).position()).length() for pt in roots)
                rms=math.sqrt(sum((pt.position()-goal.point(pt.number()).position()).lengthSquared() for pt in geo.points())/len(pos))
                item={'part':label,'frame':frame,'points':len(pos),'roots':len(roots),'max_pin_error':root_error,'rms_from_kinematic_target':rms}
                report['checks'].append(item);print(json.dumps(item),flush=True)
        if frame%12==0:print('FRAME',frame,'elapsed',round(time.time()-t,1),flush=True)
    report['elapsed_seconds']=round(time.time()-t,2)
    (path.parent/'simulation_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SIMULATION CACHES COMPLETE',flush=True)
if __name__=='__main__':main()
