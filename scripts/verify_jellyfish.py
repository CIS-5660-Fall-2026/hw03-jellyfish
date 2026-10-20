"""Verify anatomy, required nodes, deformation, cached dynamics and fallback."""
from pathlib import Path
from collections import Counter
import argparse,json,math
import hou

def components(geo):
    parent=list(range(len(geo.points())))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for prim in geo.prims():
        pts=[v.point().number() for v in prim.vertices()]
        for q in pts[1:]:parent[find(q)]=find(pts[0])
    return len({find(i) for i in range(len(parent))})


def main():
    p=argparse.ArgumentParser();p.add_argument('hip');args=p.parse_args();path=Path(args.hip).resolve()
    hou.hipFile.load(str(path),suppress_save_prompt=True)
    a=hou.node('/obj/jellyfish/jellyfish_generator');assert a.type().definition().libraryFilePath()=='Embedded'
    assert not a.spareParms()
    environment=hou.node('/obj/seafloor_environment')
    assert environment and environment.displayNode().geometry().prims()
    rock_bounds=[]
    for i in range(1,7):
        rock=environment.node(f'rock_{i}_placement');geo=rock.geometry()
        assert geo.prims() and not rock.errors()
        box=geo.boundingBox()
        assert abs(box.minvec().y()+9.27)<.001
        rock_bounds.append({'min':list(box.minvec()),'max':list(box.maxvec())})
    for n in environment.children():assert not n.errors(),(n.path(),n.errors())
    assert max(abs(v) for v in hou.node('/obj/jellyfish').parmTuple('r').eval())<1e-8
    required={'revolve_bell':'revolve','bend_bell_main':'bend','bend_bell_tip':'bend',
              'triangulate_bell_for_veins':'remesh::2.0','FIND_SHORTEST_PATH_VEINS':'findshortestpath',
              'SWEEP_VEIN_WIDTH':'sweep::2.0','POINT_DEFORM_VEINS':'pointdeform',
              'point_deform_arm_targets':'pointdeform','arms_cloth_constraints':'vellumconstraints',
              'ARMS_VELLUM_SOLVER':'vellumsolver','tentacle_hair_constraints':'vellumconstraints',
              'TENTACLES_VELLUM_SOLVER':'vellumsolver'}
    for name,typ in required.items():
        actual=a.node(name).type().name()
        assert actual.split('::')[0]==typ.split('::')[0],(name,actual,typ)
    hou.setFrame(1)
    assert len(a.node('four_horseshoe_organs').geometry().prims())==4
    assert components(a.node('copy_oral_arms').geometry())==a.evalParm('arm_count')
    hair=a.node('rim_tentacle_curves').geometry()
    assert len(hair.prims())==a.evalParm('tentacle_count')
    assert len(hair.findPointGroup('tentacle_roots').points())==a.evalParm('tentacle_count')
    triangles=a.node('triangulate_bell_for_veins').geometry()
    assert all(len(p.vertices())==3 for p in triangles.prims())
    paths=a.node('FIND_SHORTEST_PATH_VEINS').geometry()
    assert len(paths.prims())==a.evalParm('vein_count')
    shell=a.node('bell_membrane_thickness').geometry();edgecount=Counter()
    for prim in shell.prims():
        pts=[v.point().number() for v in prim.vertices()]
        for x,y in zip(pts,pts[1:]+pts[:1]):
            if x!=y:edgecount[tuple(sorted((x,y)))]+=1
    assert all(v==2 for v in edgecount.values()),Counter(edgecount.values())
    diagnostics=hou.node('/obj').createNode('geo','validation_probe')
    parts=[]
    for src in ('POINT_DEFORM_VEINS','BELL_ANIMATED_SURFACE'):
        n=diagnostics.createNode('object_merge');n.parm('objpath1').set(a.node(src).path());parts.append(n)
    probe=diagnostics.createNode('attribwrangle');probe.setInput(0,parts[0]);probe.setInput(1,parts[1])
    probe.parm('class').set(probe.parm('class').menuLabels().index('Points'))
    probe.parm('snippet').set('f@surface_error=xyzdist(1,@P);')
    sample_results=[];radii=[];pointcounts=[]
    for frame in (37,60,84,108,144,180):
        hou.setFrame(frame);a.cook(force=True)
        for n in (a,*a.children()):
            assert not n.errors(),(n.path(),n.errors())
        for part in ('BELL','ARMS','VEINS','ORGANS','TENTACLES'):
            assert a.node('OUT_'+part).geometry().prims(),part
        # Thin-shell extrusion must not produce spikes at sharp simulated folds.
        cloth_box=a.node('soft_arm_folds').geometry().boundingBox()
        shell_box=a.node('oral_arm_thickness').geometry().boundingBox()
        for axis in range(3):
            assert shell_box.minvec()[axis]>=cloth_box.minvec()[axis]-.02,(frame,'arm shell minimum',axis)
            assert shell_box.maxvec()[axis]<=cloth_box.maxvec()[axis]+.02,(frame,'arm shell maximum',axis)
        shell_expansion=max(max(cloth_box.minvec()[i]-shell_box.minvec()[i],shell_box.maxvec()[i]-cloth_box.maxvec()[i]) for i in range(3))
        bell=a.node('BELL_ANIMATED_SURFACE').geometry();radii.append(bell.boundingBox().sizevec().x());pointcounts.append(len(bell.points()))
        distances=sorted(probe.geometry().pointFloatAttribValues('surface_error'))
        q95=distances[int(len(distances)*.95)]
        assert q95<.15,(frame,q95)
        sample_results.append({'frame':frame,'bell_width':radii[-1],'vein_surface_distance_p95':q95,'arm_shell_bbox_expansion':shell_expansion})
    assert len(set(pointcounts))==1
    assert max(radii)-min(radii)>.1
    sim=json.loads((path.parent/'simulation_validation.json').read_text())
    assert sim['frame_range']==[1,180]
    for kind in ('arms','tentacles'):
        records=[x for x in sim['checks'] if x['part']==kind]
        assert max(x['max_pin_error'] for x in records)<1e-4
        assert max(x['rms_from_kinematic_target'] for x in records)>.1
        assert all((path.parent/'cache'/f'{kind}.{f:04d}.bgeo.sc').exists() for f in range(1,181))
    # Verify that the HIP can evaluate its live solvers without relying on caches.
    hou.setFrame(1);a.parm('use_cache').set(0);a.cook(force=True)
    assert a.geometry().prims() and not a.errors()
    report={'houdini':hou.applicationVersionString(),'embedded_hda':a.type().name(),'required_nodes_verified':required,
            'arms':a.evalParm('arm_count'),'organs':4,'tentacles':a.evalParm('tentacle_count'),'vein_paths':len(paths.prims()),
            'bell_closed_manifold':True,'live_solver_fallback_passed':True,'samples':sample_results,
            'max_sampled_pin_error':max(x['max_pin_error'] for x in sim['checks']), 'simulation_frames':180,
            'environment_rocks':6,'rock_bounds':rock_bounds,'upright_pose':True,'passed':True}
    (path.parent/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));print('ALL NATIVE JELLYFISH CHECKS PASSED')
if __name__=='__main__':main()
