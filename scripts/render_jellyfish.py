"""Render a native Mantra image from the saved project."""
from pathlib import Path
import argparse,os
import hou

def main():
    p=argparse.ArgumentParser();p.add_argument('hip');p.add_argument('--frame',type=int,default=73);p.add_argument('--preview',action='store_true');p.add_argument('--close-up',action='store_true');p.add_argument('--threads',type=int,default=4);args=p.parse_args()
    path=Path(args.hip).resolve();hou.hipFile.load(str(path),suppress_save_prompt=True);hou.setFrame(args.frame)
    os.environ['PATH']=hou.text.expandString('$HFS/bin')+os.pathsep+os.environ.get('PATH','')
    r=hou.node('/out/jellyfish_beauty')
    r.parm('soho_pipecmd').set(f'mantra -j {args.threads}')
    image=path.parent/'media'/('jellyfish-preview.png' if args.preview else 'jellyfish-beauty.png')
    if args.close_up:
        image=path.parent/'media'/'jellyfish-detail.png'
        cam=hou.node('/obj/jellyfish_camera');pos=hou.Vector3(0,1.8,22);target=hou.Vector3(0,-.2,0)
        cam.setWorldTransform(hou.hmath.buildRotateLookAt(pos,target,hou.Vector3(0,1,0))*hou.hmath.buildTranslate(pos))
        cam.setParms({'orthowidth':6.5,'resx':1024,'resy':768})
    r.setParms({'vm_samplesx':4,'vm_samplesy':4})
    r.parm('vm_picture').set(str(image))
    if args.preview:
        hou.node('/obj/jellyfish_camera').parmTuple('res').set((576,720))
        r.setParms({'vm_samplesx':2,'vm_samplesy':2,'vm_maxraysamples':3})
    print('RENDERING',image,flush=True);r.render();print('RENDER COMPLETE',image,flush=True)
if __name__=='__main__':main()
