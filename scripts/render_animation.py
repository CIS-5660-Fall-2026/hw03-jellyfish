"""Render cached simulation frames with native Mantra, without a GUI."""
from pathlib import Path
import argparse,os,time
import hou

def main():
    p=argparse.ArgumentParser();p.add_argument('hip');p.add_argument('--start',type=int,default=37);p.add_argument('--end',type=int,default=179);p.add_argument('--step',type=int,default=2);p.add_argument('--threads',type=int,default=4)
    p.add_argument('--width',type=int,default=576);p.add_argument('--height',type=int,default=720);p.add_argument('--samples',type=int,default=3);p.add_argument('--output-dir',default='motion_frames');args=p.parse_args()
    path=Path(args.hip).resolve();hou.hipFile.load(str(path),suppress_save_prompt=True)
    os.environ['PATH']=hou.text.expandString('$HFS/bin')+os.pathsep+os.environ.get('PATH','')
    cam=hou.node('/obj/jellyfish_camera');cam.parmTuple('res').set((args.width,args.height))
    rop=hou.node('/out/jellyfish_beauty')
    rop.setParms({'vm_renderengine':'raytrace','vm_samplesx':args.samples,'vm_samplesy':args.samples,'vm_minraysamples':1,'vm_maxraysamples':1,'vm_reflectlimit':0,'vm_diffuselimit':0})
    rop.parm('soho_pipecmd').set(f'mantra -j {args.threads}')
    directory=path.parent/args.output_dir;directory.mkdir(exist_ok=True)
    t=time.time()
    for frame in range(args.start,args.end+1,args.step):
        hou.setFrame(frame);output=directory/f'jellyfish.{frame:04d}.png'
        if output.exists() and output.stat().st_size>1000:continue
        rop.parm('vm_picture').set(str(output));rop.render(frame_range=(frame,frame))
        print('RENDERED',frame,'elapsed',round(time.time()-t,1),flush=True)
    print('MOTION RENDER COMPLETE',flush=True)
if __name__=='__main__':main()
