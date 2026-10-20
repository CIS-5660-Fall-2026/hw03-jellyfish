"""Build the assignment's five parts with native Houdini SOPs and Vellum."""
from pathlib import Path
import json, os
import hou
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=Path(os.environ.get('JELLYFISH_OUTPUT_DIR',str(ROOT/'local_output'))).resolve()
START,END,VIDEO_START=1,180,37
PARAMS={'bell_size':4.0,'pulse_amount':.70,'pulse_speed':.52,'scallops':.065,
        'arm_count':4,'arm_length':5.7,'arm_width':1.1,'tentacle_count':32,
        'tentacle_length':8.3,'vein_count':48,'current_strength':.24}
LOOKS={'bell':((.92,.47,.035),.32,.02),'arms':((.90,.79,.52),.38,.025),
       'veins':((1.0,.72,.20),.65,.03),'organs':((.88,.49,.05),.88,.02),
       'tentacles':((.11,.012,.004),1,.02),'rim':((.46,.12,.016),.90,.02)}


def menu(n,key,label):
    p=n.parm(key);i=[v.lower() for v in p.menuLabels()].index(label.lower())
    p.set(p.menuItems()[i] if p.parmTemplate().type()==hou.parmTemplateType.String else i)


def vals(n,settings):
    for key,value in settings.items():
        p=n.parm(key)
        if p is None:raise RuntimeError(f'Missing parameter {n.path()}/{key}')
        if isinstance(value,str) and p.parmTemplate().type() in (hou.parmTemplateType.Float,hou.parmTemplateType.Int):
            p.setExpression(value,hou.exprLanguage.Hscript)
        else:p.set(value)
    return n


def node(a,typ,name,src=None,params=None):
    n=a.createNode(typ,name)
    if src is not None:n.setInput(0,src)
    if params:vals(n,params)
    return n


def wrangle(a,name,code,src=None,mode='Detail (only once)',second=None):
    n=node(a,'attribwrangle',name,src);menu(n,'class',mode);n.parm('snippet').set(code)
    if second is not None:n.setInput(1,second)
    return n


def null(a,name,src):return node(a,'null',name,src)


def controls(a):
    g=hou.ParmTemplateGroup()
    labels={'bell_size':'Bell Size','pulse_amount':'Pulse Amount','pulse_speed':'Pulse Speed',
            'scallops':'Scalloped Rim','arm_count':'Arm Count','arm_length':'Arm Length','arm_width':'Arm Width',
            'tentacle_count':'Tentacle Count','tentacle_length':'Tentacle Length','vein_count':'Vein Endpoints',
            'current_strength':'Water Current'}
    limits={'bell_size':(3,5),'pulse_amount':(0,1.4),'pulse_speed':(.3,1), 'scallops':(0,.08),
            'arm_count':(3,7),'arm_length':(3,7),'arm_width':(.45,1.5),'tentacle_count':(16,80),
            'tentacle_length':(2,10),'vein_count':(24,64),'current_strength':(0,.8)}
    for k,v in PARAMS.items():
        cls=hou.IntParmTemplate if isinstance(v,int) else hou.FloatParmTemplate
        lo,hi=limits[k]
        g.append(cls(k,labels[k],1,default_value=(v,),min=lo,max=hi,min_is_strict=True,max_is_strict=True))
    # Appearance controls do not change the simulation cache signature.
    g.append(hou.FloatParmTemplate('bell_opacity','Bell Opacity',1,default_value=(.32,),min=.05,max=1,min_is_strict=True,max_is_strict=True))
    g.append(hou.FloatParmTemplate('arm_opacity','Oral Arm Opacity',1,default_value=(.38,),min=.05,max=1,min_is_strict=True,max_is_strict=True))
    g.append(hou.ToggleParmTemplate('use_cache','Use Matching Simulation Cache',default_value=True))
    p=hou.StringParmTemplate('cache_signature','Cache Signature',1,default_value=(str([round(float(v),6) for v in PARAMS.values()]),))
    p.hide(True);g.append(p);a.setParmTemplateGroup(g)


def finish(a,src,part):
    clean=wrangle(a,part+'_clean_attributes','''
string pointattrs[]=detailintrinsic(0,"pointattributes");
foreach(string attr;pointattrs)if(find(array("P","profile_u","arm_u","arm_edge"),attr)<0)removeattrib(0,"point",attr);
string primattrs[]=detailintrinsic(0,"primitiveattributes");
foreach(string attr;primattrs)removeattrib(0,"prim",attr);
string vertattrs[]=detailintrinsic(0,"vertexattributes");
foreach(string attr;vertattrs)removeattrib(0,"vertex",attr);
''',src)
    color,alpha,emit=LOOKS[part]
    code=f'v@Cd=set({color[0]},{color[1]},{color[2]}); f@Alpha={alpha};'
    if part=='bell':
        code+='''
float u=clamp(f@profile_u,0,1),a=atan2(@P.z,@P.x);
vector coord=set(cos(a)*2,sin(a)*2,u*3);
float grain=noise(coord*5.5+13),marble=noise(coord*2+4);
float stripe=pow(.5+.5*cos(a*16+.4*sin(u*11+a*3)),5);
float ridge=pow(.5+.5*cos(a*32+.3*sin(u*17)),16);
float edge=pow(1-u,4);
vector gold=lerp(set(.48,.14,.008),set(.93,.49,.03),.25+.7*marble);
gold=lerp(gold,set(.27,.045,.003),stripe*(.30+.45*edge));
gold=lerp(gold,set(1,.70,.12),ridge*.16);
v@Cd=gold*(.88+.22*grain);
f@Alpha=clamp((.27+.10*edge+.05*stripe)*ch("../bell_opacity")/.32,.01,1);
'''
    elif part=='arms':
        code+='''
float n=noise(set(f@arm_u*13,f@arm_edge*3,2));
v@Cd=lerp(set(.73,.55,.24),set(1.0,.93,.73),.48+.45*n);
f@Alpha=clamp(lerp(.50,.26,pow(clamp(f@arm_edge,0,1),1.2))*ch("../arm_opacity")/.38,.01,1);
'''
    colored=wrangle(a,part+'_color',code,clean,'Points')
    tagged=wrangle(a,part+'_material',f's@part="{part}"; s@shop_materialpath="/mat/{part}"; @group_{part}=1;',colored,'Primitives')
    return null(a,'OUT_'+part.upper(),tagged)


def tube(a,name,src,radius,cols=8):
    clean=wrangle(a,name+'_remove_sim_scale','removeattrib(0,"point","pscale"); removeattrib(0,"point","orient"); removeattrib(0,"point","scale");',src)
    n=node(a,'sweep::2.0',name,clean,{'radius':radius,'cols':cols})
    menu(n,'surfaceshape','Round Tube');menu(n,'endcaptype','Single Polygon')
    return n


def deform(a,name,src,rest,animated,radius=.6,minpt=4,maxpt=12):
    n=node(a,'pointdeform',name,src,{'radius':radius,'minpt':minpt,'maxpt':maxpt})
    n.setInput(1,rest);n.setInput(2,animated)
    return n


def cache_switch(a,solver,name):
    f=node(a,'file',name+'_cache',params={'file':f'$HIP/cache/{name}.$F4.bgeo.sc'})
    sw=node(a,'switch',name+'_cache_or_sim',solver);sw.setInput(1,f)
    keys=repr(list(PARAMS))
    expr=f'''n=hou.pwd().parent()
p=hou.expandString("$HIP/cache/{name}.$F4.bgeo.sc")
s=str([round(float(n.evalParm(k)),6) for k in {keys}])
return int(n.evalParm("use_cache") and s==n.evalParm("cache_signature") and __import__("os").path.isfile(p))'''
    sw.parm('input').setExpression(expr,hou.exprLanguage.Python)
    return sw


def solver(a,name,constraints,force_scale):
    n=node(a,'vellumsolver',name)
    n.setInput(0,constraints,0);n.setInput(1,constraints,1)
    vals(n,{'substeps':3,'niter':60,'smoothiter':5,'gravityy':-.3,
            'windx':'ch("../current_strength")*.35','windz':'ch("../current_strength")*.14',
            'winddrag':.45,'veldamping':.03,'angveldamping':.03,'startframe':1})
    forces=n.node('dopnet1/forces')
    force=forces.createNode('popforce','water_current')
    rel=force.relativePathTo(a)
    vals(force,{'amp':f'ch("{rel}/current_strength")*{force_scale}',
                'swirlsize':1.5,'pulselength':2.5,'rough':.25})
    forces.node('FORCE').setInput(0,force);forces.layoutChildren()
    return n


def bell(a):
    ctrl=node(a,'null','BELL_ANIMATION')
    group=hou.ParmTemplateGroup()
    for name,label in [('bend_main','Main Bend'),('bend_tip','Rim Bend'),('bob','Vertical Motion')]:
        group.append(hou.FloatParmTemplate(name,label,1))
    ctrl.setParmTemplateGroup(group);ctrl.setColor(hou.Color((.15,.45,.8)))
    ctrl.setUserData('nodeshape','circle')
    phase='max(0,($F-37)/$FPS)*ch("../pulse_speed")*360'
    vals(ctrl,{'bend_main':f'88+7*ch("../pulse_amount")*sin({phase})',
               'bend_tip':f'-10+14*ch("../pulse_amount")*sin({phase}+25)',
               'bob':f'.20*ch("../pulse_amount")*sin({phase}+15)'})
    line=node(a,'line','bell_profile_line',params={'points':48})
    profile=wrangle(a,'profile_coordinate','f@profile_u=float(@ptnum)/max(1,@numpt-1);',line,'Points')
    tip=node(a,'bend','bend_bell_tip',profile,{'originy':.2,'diry':-1,'dirz':0,'upx':-1,'upy':0,'upz':0,'length':.2,
                                            'bend':'ch("../BELL_ANIMATION/bend_tip")'})
    main=node(a,'bend','bend_bell_main',tip,{'diry':1,'dirz':0,'upx':-1,'upy':0,'upz':0,'length':1,
                                          'bend':'ch("../BELL_ANIMATION/bend_main")'})
    align=node(a,'matchsize','align_revolve_axis',main,{'justify_x':1,'justify_y':0,'justify_z':0})
    rev=node(a,'revolve','revolve_bell',align,{'divs':96})
    fused=node(a,'fuse::2.0','fuse_bell_pole',rev)
    noise=node(a,'mountain::2.0','soft_bell_noise',fused,{'height':.018,'elementsize':1.5,'rough':0})
    scallop=wrangle(a,'scalloped_bell_edge','''
float angle=atan2(@P.z,@P.x),rim=pow(1-f@profile_u,7);
vector radial=normalize(set(@P.x,0,@P.z));
@P+=radial*ch("../scallops")*.3*cos(angle*16)*rim;
@P.y+=ch("../scallops")*.25*sin(angle*16)*rim;
@P+=radial*.009*cos(angle*32)*sin(f@profile_u*M_PI);
@group_bell_rim=f@profile_u<.001;
''',noise,'Points')
    motion=node(a,'xform','bell_size_and_motion',scallop,{'scale':'ch("../bell_size")','sy':.82,'ty':'ch("../BELL_ANIMATION/bob")'})
    surface=null(a,'BELL_ANIMATED_SURFACE',motion)
    rest=node(a,'timeshift','BELL_REST_SURFACE',surface)
    rest.parm('frame').deleteAllKeyframes();rest.parm('frame').set(1)
    skin=node(a,'subdivide','smooth_bell_skin',surface,{'iterations':1})
    shell=node(a,'polyextrude::2.0','bell_membrane_thickness',skin,{'dist':.035,'outputback':1})
    out=finish(a,shell,'bell')
    centroid=node(a,'extractcentroid','BELL_CENTROID',surface);menu(centroid,'partitiontype','Detail')
    center_rest=node(a,'timeshift','BELL_REST_CENTROID',centroid)
    center_rest.parm('frame').deleteAllKeyframes();center_rest.parm('frame').set(1)
    return surface,rest,out,centroid,center_rest


def arms(a,rest,center,center_rest):
    grid=node(a,'grid','oral_arm_grid',params={'sizex':'ch("../arm_width")','sizey':'ch("../arm_length")','rows':180,'cols':21})
    menu(grid,'orient','XY Plane')
    ruffles=wrangle(a,'ruffle_arm_edges','''
f@arm_u=clamp((ch("../arm_length")*.5-@P.y)/ch("../arm_length"),0,1);
f@arm_edge=abs(@P.x)/(ch("../arm_width")*.5);
float edge=pow(f@arm_edge,1.5);
@P.x*=lerp(1,.22,pow(f@arm_u,2))*(.92+.08*sin(@P.y*4));
@P.z+=edge*(.17*sin(@P.y*19)+.075*sin(@P.y*43)+.025*snoise(@P*7));
@P.y+=edge*.035*sin(@P.y*37+f@arm_edge*5);
''',grid,'Points')
    twist=node(a,'bend','twist_oral_arm',ruffles,{'enablebend':0,'enabletwist':1,'twist':460,
            'originy':'-ch("../arm_length")*.5','diry':1,'dirz':0,'upx':1,'upy':0,'upz':0,'length':'ch("../arm_length")'})
    remesh=node(a,'remesh::2.0','remesh_twisted_arm',twist,{'targetsize':.060,'iterations':2})
    align=node(a,'matchsize','align_arm_top_for_pins',remesh,{'justify_x':0,'justify_y':3,'justify_z':0})
    pin_group=wrangle(a,'group_arm_roots','@group_arm_roots=@P.y>-.045;',align,'Points')
    points=wrangle(a,'radial_arm_positions','''
vector lo=getbbox_min(0),hi=getbbox_max(0); float rad=max(hi.x,-lo.x)*.20;
for(int i=0;i<chi("../arm_count");i++){
 float ang=2*M_PI*i/chi("../arm_count");
 int p=addpoint(0,set(rad*cos(ang),lo.y+.25,rad*sin(ang)));
 vector4 q=quaternion(-ang,set(0,1,0));setpointattrib(0,"orient",p,q,"set");
}
for(int i=nprimitives(0)-1;i>=0;i--)removeprim(0,i,1);
''',rest)
    # Only the generated placement points should remain after deleting the bell.
    copies=node(a,'copytopoints::2.0','copy_oral_arms',pin_group);copies.setInput(1,points)
    targets=deform(a,'point_deform_arm_targets',copies,center_rest,center,4,1,1)
    cloth=node(a,'vellumconstraints','arms_cloth_constraints',targets)
    menu(cloth,'constrainttype','Cloth')
    vals(cloth,{'stretchstiffness':1,'stretchstiffnessexp':7,'stretchdampingratio':.001,
                'bendstiffness':1,'bendstiffnessexp':-2,'benddampingratio':.05,'thickness':.014})
    menu(cloth,'domass','Set Uniform');cloth.parm('mass').set(.005)
    menu(cloth,'dothickness','Set Uniform')
    pins=node(a,'vellumconstraints','arms_pin_to_animation',cloth)
    pins.setInput(1,cloth,1);menu(pins,'constrainttype','Pin to Target');menu(pins,'grouptype','Points')
    vals(pins,{'group':'arm_roots','matchanimation':1})
    sim=solver(a,'ARMS_VELLUM_SOLVER',pins,.20)
    cached=cache_switch(a,sim,'arms')
    soft=node(a,'subdivide','soft_arm_folds',cached,{'iterations':1})
    thickness=node(a,'polyextrude::2.0','oral_arm_thickness',soft,{'dist':.008,'outputback':1})
    # Point normals avoid unbounded miter offsets at tightly folded cloth edges.
    menu(thickness,'extrusionmode','Point Normal')
    return finish(a,thickness,'arms')


def veins(a,rest,animated):
    tri=node(a,'remesh::2.0','triangulate_bell_for_veins',rest,{'targetsize':.13,'iterations':2})
    cost=wrangle(a,'organic_vein_cost','f@vein_cost=.02+.09*noise(@P*2.8+17);',tri,'Points')
    seeds=wrangle(a,'vein_start_end_points','''
vector lo=getbbox_min(0),hi=getbbox_max(0);float rad=max(hi.x,-lo.x);
for(int k=0;k<4;k++){
 float ang=2*M_PI*k/4;int p=addpoint(0,set(.18*rad*cos(ang),hi.y-.05,.18*rad*sin(ang)));
 setpointgroup(0,"vein_roots",p,1);
}
for(int k=0;k<chi("../vein_count");k++){
 float ang=2*M_PI*(k+.15*rand(k+9))/chi("../vein_count");
 int p=addpoint(0,set(rad*.98*cos(ang),lo.y+.12,rad*.98*sin(ang)));
 setpointgroup(0,"vein_ends",p,1);
}
for(int i=nprimitives(0)-1;i>=0;i--)removeprim(0,i,1);
''',rest)
    path=node(a,'findshortestpath','FIND_SHORTEST_PATH_VEINS',cost)
    path.setInput(1,seeds);menu(path,'multiplicity','From any start to each end')
    vals(path,{'startpts':'vein_roots','endpts':'vein_ends','enablecost':1,'cost':'vein_cost','enableoutputcost':0})
    fuse=node(a,'fuse::2.0','fuse_shared_vein_points',path)
    dedup=wrangle(a,'remove_shared_edge_duplicates','''
string seen[];int old=nprimitives(0);
for(int p=0;p<old;p++){
 int pts[]=primpoints(0,p);
 for(int j=0;j<len(pts)-1;j++){
  int x=min(pts[j],pts[j+1]),y=max(pts[j],pts[j+1]);string key=sprintf("%d_%d",x,y);
  if(find(seen,key)<0){append(seen,key);int pr=addprim(0,"polyline");addvertex(0,pr,x);addvertex(0,pr,y);}
 }
}
for(int p=old-1;p>=0;p--)removeprim(0,p,0);
''',fuse)
    paths=node(a,'polypath','connect_vein_branches',dedup)
    resample=node(a,'resample','resample_veins',paths,{'length':.055})
    smooth=node(a,'smooth::2.0','smooth_veins',resample,{'strength':3,'contrainedboundary':0})
    project=wrangle(a,'project_veins_to_bell','''
int pr;vector uv;xyzdist(1,@P,pr,uv);
@P=primuv(1,"P",pr,uv)+prim_normal(1,pr,uv)*.025;
''',smooth,'Points',rest)
    width=tube(a,'SWEEP_VEIN_WIDTH',project,.009,6)
    moved=deform(a,'POINT_DEFORM_VEINS',width,rest,animated,.5,4,16)
    return finish(a,moved,'veins')


def organs(a,rest,animated):
    curves=wrangle(a,'four_horseshoe_organs','''
vector lo=getbbox_min(0),hi=getbbox_max(0);float y=lo.y+(hi.y-lo.y)*.48;int old=nprimitives(0);
for(int i=0;i<4;i++){
 float a=2*M_PI*i/4; vector radial=set(cos(a),0,sin(a)),side=set(-sin(a),0,cos(a));
 vector center=radial*.60+set(0,y,0);int prim=addprim(0,"polyline");
 for(int j=0;j<40;j++){
  float t=radians(-35+float(j)/39*285);
  vector pos=center+radial*(.33*cos(t))+side*(.25*sin(t))+set(0,.03*sin(2*t+i),0);
  int p=addpoint(0,pos);addvertex(0,prim,p);
 }
}
for(int p=old-1;p>=0;p--)removeprim(0,p,1);
''',rest)
    width=tube(a,'organ_tissue',curves,.075,10)
    moved=deform(a,'organs_follow_bell',width,rest,animated,.8,4,16)
    return finish(a,moved,'organs')


def tentacles(a,rest,animated):
    curves=wrangle(a,'rim_tentacle_curves','''
vector lo=getbbox_min(0),hi=getbbox_max(0);float rad=max(hi.x,-lo.x);
int old=nprimitives(0);int count=chi("../tentacle_count");
for(int i=0;i<count;i++){
 float ang=2*M_PI*i/count;vector dir=set(cos(ang),0,sin(ang));
 int root=nearpoint(0,"bell_rim",dir*rad+set(0,lo.y,0));vector base=point(0,"P",root);
 float len=ch("../tentacle_length")*(.62+.38*rand(i+51));int pr=addprim(0,"polyline");
 for(int j=0;j<80;j++){
  float u=float(j)/79;vector p=base+set(.18*sin(u*7+i)*u,-len*u,.14*cos(u*6+i*.7)*u);
  int pt=addpoint(0,p);addvertex(0,pr,pt);setpointattrib(0,"strand_id",pt,i,"set");
  if(j==0)setpointgroup(0,"tentacle_roots",pt,1);
 }
}
for(int p=old-1;p>=0;p--)removeprim(0,p,1);
''',rest)
    targets=deform(a,'point_deform_tentacle_targets',curves,rest,animated,.4,4,12)
    hair=node(a,'vellumconstraints','tentacle_hair_constraints',targets)
    menu(hair,'constrainttype','Hair')
    vals(hair,{'pingroup':'tentacle_roots','matchanimation':1,'stretchstiffness':1,'stretchstiffnessexp':7,
               'bendstiffness':1,'bendstiffnessexp':-3,'stretchdampingratio':.01,'benddampingratio':.06,
               'thickness':.009,'mass':.002})
    menu(hair,'domass','Set Uniform');menu(hair,'dothickness','Set Uniform')
    sim=solver(a,'TENTACLES_VELLUM_SOLVER',hair,.12)
    cached=cache_switch(a,sim,'tentacles')
    smooth=node(a,'resample','smooth_tentacle_curves',cached,{'length':.055})
    menu(smooth,'treatpolysas','Subdivision Curves')
    thick=tube(a,'tentacle_render_width',smooth,.019,8)
    thick.parm('applyscale').set(1)
    thick.parm('scaleramp').set(hou.Ramp((hou.rampBasis.Linear,hou.rampBasis.Linear),(0,1),(1,.40)))
    return finish(a,thick,'tentacles')


def rim(a,rest,animated):
    curve=wrangle(a,'bell_rim_curve','''
vector lo=getbbox_min(0),hi=getbbox_max(0);float rad=max(hi.x,-lo.x);
int old=nprimitives(0);int pr=addprim(0,"polyline");
for(int i=0;i<=96;i++){
 float t=2*M_PI*(i%96)/96;int pt=nearpoint(0,"bell_rim",set(rad*cos(t),lo.y,rad*sin(t)));
 vector pos=point(0,"P",pt);int q=addpoint(0,pos);addvertex(0,pr,q);
}
for(int p=old-1;p>=0;p--)removeprim(0,p,1);
''',rest)
    smooth=node(a,'resample','smooth_bell_rim',curve,{'length':.045})
    menu(smooth,'treatpolysas','Subdivision Curves')
    thick=tube(a,'rim_tissue',smooth,.022,8)
    return finish(a,deform(a,'rim_follow_bell',thick,rest,animated,.4,4,12),'rim')


def materials():
    for name,(color,alpha,emit) in LOOKS.items():
        n=hou.node('/mat').createNode('principledshader::2.0',name)
        n.parmTuple('basecolor').set((1,1,1));n.parm('basecolor_usePointColor').set(1)
        n.parm('rough').set(.34 if name=='bell' else .48)
        n.parm('reflect').set(.30 if name=='bell' else .10)
        n.parm('sss').set(0)
        n.parmTuple('ssscolor').set(color);n.parm('sssdist').set(.07)
        n.parm('emitint').set(emit);n.parmTuple('emitcolor').set(color)
    bg=hou.node('/mat').createNode('principledshader::2.0','deep_water')
    bg.parmTuple('basecolor').set((0,0,0));bg.parm('rough').set(1)
    bg.parm('reflect').set(0)
    bg.parm('emitint').set(1);bg.parmTuple('emitcolor').set((.006,.050,.17))
    bg.parm('emitcolor_usePointColor').set(1)
    for name in ('seafloor_sand','seafloor_rock'):
        m=hou.node('/mat').createNode('principledshader::2.0',name)
        m.parmTuple('basecolor').set((1,1,1));m.parm('basecolor_usePointColor').set(1)
        m.parm('rough').set(.92);m.parm('reflect').set(.035)
        m.parm('emitint').set(.08);m.parmTuple('emitcolor').set((.025,.07,.11))
    hou.node('/mat').layoutChildren()


def seabed():
    env=hou.node('/obj').createNode('geo','seafloor_environment')
    for n in env.children():n.destroy()
    ground=node(env,'grid','seabed_grid',params={'sizex':50,'sizey':50,'rows':151,'cols':151})
    menu(ground,'orient','ZX Plane')
    sand=wrangle(env,'sand_ripples_and_depth_fade','''
vector q=@P;
float ripple=sin(q.x*7+.8*sin(q.z*.55))*.018;
@P.y=-9.2+ripple+.055*snoise(q*.36);
float n=noise(q*1.9+11);
v@Cd=lerp(set(.028,.060,.077),set(.075,.13,.15),n);
float depth=clamp((-q.z-2)/24,0,1);
v@Cd=lerp(v@Cd,set(.025,.080,.16),depth*.7);
f@Alpha=1-smooth(0,15,-q.z);
''',ground,'Points')
    sand=wrangle(env,'sand_material','s@shop_materialpath="/mat/seafloor_sand"; s@environment_part="seabed";',sand,'Primitives')
    parts=[sand]
    # (x, z, width, height, depth, yaw): larger rocks behind, smaller ones near the sides.
    placements=[(-4.1,-2.4,3.2,2.0,2.6,20),(4.0,-3.4,3.4,2.5,2.6,-25),
                (-2.7,-5.5,2.1,1.4,1.7,-15),(2.4,-7.0,2.7,1.7,2.3,42),
                (-4.6,2.1,1.9,1.1,1.4,10),(3.8,3.0,1.8,.9,1.4,-20)]
    for i,(x,z,sx,sy,sz,ry) in enumerate(placements):
        box=node(env,'box',f'rock_{i+1}_base')
        rounded=node(env,'subdivide',f'rock_{i+1}_rounded',box,{'iterations':4})
        shaped=wrangle(env,f'rock_{i+1}_eroded',f'''
vector q=@P;float seed={i*7+13};
@P*=1+.32*snoise(q*3.8+seed)+.07*snoise(q*13+seed);
@P+=.026*set(snoise(q*8+seed),snoise(q*9+seed+4),snoise(q*7+seed+7));
float n=noise(q*5+seed),grain=noise(q*34+seed);
v@Cd=lerp(set(.035,.065,.080),set(.13,.19,.22),n)*(.85+.3*grain);
f@Alpha=1;
''',rounded,'Points')
        size=node(env,'matchsize',f'rock_{i+1}_dimensions',shaped)
        # Normalize dimensions explicitly so the stones have predictable placement.
        scaled=wrangle(env,f'rock_{i+1}_scale',f'''
vector b=getbbox_size(0);@P=set(@P.x*{sx}/b.x,@P.y*{sy}/b.y,@P.z*{sz}/b.z);
''',size,'Points')
        turned=node(env,'xform',f'rock_{i+1}_rotation',scaled,{'ry':ry,'rx':(i%3-1)*8,'rz':(i%2*2-1)*7})
        bottom=node(env,'matchsize',f'rock_{i+1}_ground_contact',turned,{'justify_x':0,'justify_y':1,'justify_z':0})
        placed=node(env,'xform',f'rock_{i+1}_placement',bottom,{'tx':x,'ty':-9.27,'tz':z})
        mat=wrangle(env,f'rock_{i+1}_material','s@shop_materialpath="/mat/seafloor_rock"; s@environment_part="rock";',placed,'Primitives')
        parts.append(mat)
    merged=node(env,'merge','assemble_seafloor')
    for i,p in enumerate(parts):merged.setInput(i,p)
    normal=node(env,'normal','seafloor_normals',merged)
    out=null(env,'OUT_SEAFLOOR',normal);out.setDisplayFlag(True);out.setRenderFlag(True)
    env.layoutChildren()
    return env


def scene():
    bg=hou.node('/obj').createNode('geo','deep_water_background')
    for n in bg.children():n.destroy()
    grid=node(bg,'grid','backdrop',params={'sizex':90,'sizey':90,'tz':-40,'rows':100,'cols':100})
    menu(grid,'orient','XY Plane')
    grad=wrangle(bg,'water_gradient','''
float glow=exp(-pow((@P.x+3)/12,2)-pow((@P.y-4)/13,2));
v@Cd=lerp(set(.15,.22,.40),set(.7,1,1),glow);
''',grid,'Points')
    mat=wrangle(bg,'background_material','s@shop_materialpath="/mat/deep_water";',grad,'Primitives')
    mat.setDisplayFlag(True);mat.setRenderFlag(True)
    seabed()
    cam=hou.node('/obj').createNode('cam','jellyfish_camera')
    pos=hou.Vector3(0,-1.1,22);target=hou.Vector3(0,-3.55,0)
    cam.setWorldTransform(hou.hmath.buildRotateLookAt(pos,target,hou.Vector3(0,1,0))*hou.hmath.buildTranslate(pos))
    cam.setParms({'projection':'ortho','orthowidth':10.6,'resx':768,'resy':960});cam.setDisplayFlag(False)
    light=hou.node('/obj').createNode('hlight::2.0','motion_key')
    menu(light,'light_type','Distant');light.parmTuple('r').set((-35,-30,0));light.parm('light_intensity').set(1.1)
    light.parmTuple('light_color').set((1,.87,.65))
    env=hou.node('/obj').createNode('envlight','ambient')
    env.parmTuple('light_color').set((.50,.64,.90));env.parm('light_intensity').set(.38)
    fill=hou.node('/obj').createNode('hlight::2.0','soft_front_fill')
    menu(fill,'light_type','Distant');fill.parmTuple('r').set((5,15,0))
    fill.parm('light_intensity').set(.38);fill.parmTuple('light_color').set((.82,.90,1))
    fill.parm('shadow_type').set(0)
    rock_light=hou.node('/obj').createNode('hlight::2.0','seabed_key')
    menu(rock_light,'light_type','Distant');rock_light.parmTuple('r').set((-45,-40,0))
    rock_light.parm('light_intensity').set(.9);rock_light.parmTuple('light_color').set((.55,.75,1))
    rock_light.parm('shadowmask').set('/obj/seafloor_environment')
    rock_light.parm('shadow_intensity').set(.7)
    hou.node('/obj/jellyfish').parm('lightmask').set('/obj/motion_key /obj/ambient /obj/soft_front_fill')
    hou.node('/obj/seafloor_environment').parm('lightmask').set('/obj/seabed_key /obj/ambient /obj/soft_front_fill')
    rop=hou.node('/out').createNode('ifd','jellyfish_beauty')
    vals(rop,{'camera':cam.path(),'vm_picture':'$HIP/media/jellyfish-beauty.png','vm_renderengine':'raytrace',
              'vm_samplesx':3,'vm_samplesy':3,'vm_minraysamples':1,'vm_maxraysamples':1,
              'soho_pipecmd':'mantra -j 8','soho_autoheadlight':0})
    for key,val in [('vm_diffuselimit',0),('vm_reflectlimit',0),('vm_refractlimit',4),('vm_transparentlimit',12)]:
        if rop.parm(key):rop.parm(key).set(val)
    hou.node('/obj').layoutChildren()


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for folder in ('media','cache','frames'): (OUTPUT/folder).mkdir(exist_ok=True)
    hou.setFps(24);hou.playbar.setFrameRange(START,END);hou.playbar.setPlaybackRange(VIDEO_START,END);hou.setFrame(1)
    materials()
    obj=hou.node('/obj').createNode('geo','jellyfish')
    for n in obj.children():n.destroy()
    a=obj.createNode('subnet','jellyfish_generator')
    for n in a.children():n.destroy()
    controls(a)
    animated,rest,bell_out,center,center_rest=bell(a)
    parts=[bell_out,arms(a,rest,center,center_rest),veins(a,rest,animated),organs(a,rest,animated),tentacles(a,rest,animated),rim(a,rest,animated)]
    merged=node(a,'merge','assemble_jellyfish')
    for i,p in enumerate(parts):merged.setInput(i,p)
    normals=node(a,'normal','final_normals',merged)
    out=null(a,'OUT_JELLYFISH',normals);out.setDisplayFlag(True);out.setRenderFlag(True)
    a.layoutChildren()
    asset=a.createDigitalAsset(name='yaotang::jellyfish::1.0',hda_file_name='Embedded',description='Procedural Jellyfish',min_num_inputs=0,max_num_inputs=0)
    controls(asset.type().definition());asset.removeSpareParms();asset.setDisplayFlag(True);asset.setRenderFlag(True)
    scene()
    asset.setCurrent(True,clear_all_selected=True)
    try:asset.cook(force=True)
    except hou.OperationFailed:pass
    errors=[(n.path(),n.errors()) for n in (asset,*asset.children()) if n.errors()]
    if errors:raise RuntimeError(errors)
    temporary=OUTPUT/'.hw03_jellyfish.tmp.hipnc'
    hou.hipFile.save(str(temporary))
    temporary.replace(OUTPUT/'hw03_jellyfish.hipnc')
    hou.hipFile.setName(str(OUTPUT/'hw03_jellyfish.hipnc'))
    print(json.dumps({'hip':hou.hipFile.path(),'houdini':hou.applicationVersionString(),
          'primitives':len(asset.geometry().prims()),'points':len(asset.geometry().points()),
          'bell_bounds':str(rest.geometry().boundingBox())},indent=2),flush=True)

if __name__=='__main__':main()
