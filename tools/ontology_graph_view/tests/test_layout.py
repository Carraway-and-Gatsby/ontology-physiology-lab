"""Geometry checks for the viewer's organic circle layout, run under node on the frozen inputs."""
import json, math, pathlib, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import build_graph as b
ROOT=pathlib.Path(__file__).resolve().parents[1]
NODE=shutil.which('node')
R=60
MARGIN=24
RUNNER="""
const GraphLayout=require(process.argv[2]);
const data=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const out={};
for(const view of ['source','model','catalog']){
  const {nodes,edges}=GraphLayout.viewSubset(data,view);
  const layout=GraphLayout.layoutGraph(nodes,edges,{groupOf:view==='catalog'?n=>n.record.node_class:null});
  out[view]={width:layout.width,height:layout.height,crossings:layout.crossings,bent:layout.bent,hidden:layout.hidden,groups:layout.groups,
    nodes:Object.fromEntries(layout.nodes),
    routes:Object.fromEntries([...layout.routes].map(([id,r])=>[id,{samples:r.samples,label:r.label,bent:r.bent}])),
    edges:edges.map(e=>({id:e.id,source:e.source,target:e.target,layer:e.layer,predicate:e.predicate}))};
}
process.stdout.write(JSON.stringify(out));
"""
# Three circles on one line with an edge A -> B that runs straight through C unless the layout moves or bends it.
FIXTURE="""
const GraphLayout=require(process.argv[2]);
const nodes=['A','B','C'].map(id=>({id,label:id,layer:'source'}));
const edge=(id,source,target)=>({id,source,target,layer:'model_reference',predicate:'p',record:{}});
const edges=[edge('dependency:ab','A','B'),edge('dependency:ac','A','C'),edge('dependency:cb','C','B')];
const initial={A:{x:0,y:0},C:{x:300,y:0},B:{x:600,y:0}};
const out={};
for(const [name,clearance] of [['on',true],['off',false]]){
  const layout=GraphLayout.layoutGraph(nodes,edges,{initial,iterations:0,refine:false,clearance});
  out[name]={nodes:Object.fromEntries(layout.nodes),routes:Object.fromEntries([...layout.routes].map(([id,r])=>[id,{samples:r.samples}])),edges};
}
process.stdout.write(JSON.stringify(out));
"""

def layout_script():
    html=(ROOT/'viewer.html').read_text(encoding='utf-8')
    return html.split('<script id="graph-layout">',1)[1].split('</script>',1)[0]

def run_node(runner,*extra):
    with tempfile.TemporaryDirectory() as temp:
        temp=pathlib.Path(temp)
        (temp/'layout.js').write_text(layout_script(),encoding='utf-8')
        (temp/'runner.js').write_text(runner,encoding='utf-8')
        (temp/'graph.json').write_text(json.dumps(b.build_graph(ROOT/'inputs')),encoding='utf-8')
        return subprocess.run([NODE,str(temp/'runner.js'),str(temp/'layout.js'),str(temp/'graph.json')],check=True,capture_output=True,text=True).stdout

def seg_dist(p,a,c):
    dx,dy=c['x']-a['x'],c['y']-a['y']; l2=dx*dx+dy*dy
    t=max(0,min(1,((p['x']-a['x'])*dx+(p['y']-a['y'])*dy)/l2)) if l2 else 0
    return math.hypot(p['x']-a['x']-t*dx,p['y']-a['y']-t*dy)

def poly_dist(p,samples):
    return min(seg_dist(p,samples[i-1],samples[i]) for i in range(1,len(samples)))

def segments_cross(a,c,d,e):
    def o(p,q,r): return (q['x']-p['x'])*(r['y']-p['y'])-(q['y']-p['y'])*(r['x']-p['x'])
    return o(a,c,d)*o(a,c,e)<0 and o(d,e,a)*o(d,e,c)<0

def count_crossings(view):
    n=0
    for i,e in enumerate(view['edges']):
        for f in view['edges'][i+1:]:
            if {e['source'],e['target']}&{f['source'],f['target']}: continue
            a,c=view['routes'][e['id']]['samples'],view['routes'][f['id']]['samples']
            if any(segments_cross(a[x-1],a[x],c[y-1],c[y]) for x in range(1,len(a)) for y in range(1,len(c))): n+=1
    return n

def clearance_violations(view):
    found=[]
    for e in view['edges']:
        for node_id,node in view['nodes'].items():
            if node_id in (e['source'],e['target']): continue
            if poly_dist(node,view['routes'][e['id']]['samples'])<node['r']: found.append((e['id'],node_id))
    return found

def label_rect(label):
    return (label['x']-label['w']/2,label['y']-label['h']/2,label['x']+label['w']/2,label['y']+label['h']/2)

def rect_hits_circle(r,node):
    nx,ny=max(r[0],min(node['x'],r[2])),max(r[1],min(node['y'],r[3]))
    return math.hypot(nx-node['x'],ny-node['y'])<node['r']

def rects_overlap(a,c):
    return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]

@unittest.skipUnless(NODE,'node is required to run the viewer layout')
class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=run_node(RUNNER); cls.views=json.loads(cls.raw)

    def test_routes_clear_every_unrelated_node(self):
        for view in ('source','model'):
            self.assertEqual(clearance_violations(self.views[view]),[],view)

    def test_clearance_checking_is_not_disabled(self):
        # The fixture puts C on the straight line A -> B. With clearance checking off the line runs through C;
        # with it on, the layout must move or bend. This fails if the layout stops checking edge/node clearance.
        fixture=json.loads(run_node(FIXTURE))
        self.assertTrue(clearance_violations(fixture['off']),'fixture no longer exercises the clearance check')
        self.assertEqual(clearance_violations(fixture['on']),[])

    def test_nodes_are_circles_and_do_not_overlap(self):
        for view,v in self.views.items():
            boxes=list(v['nodes'].items())
            for i,(a,na) in enumerate(boxes):
                self.assertEqual(na['r'],R)
                for c,nc in boxes[i+1:]:
                    self.assertGreaterEqual(math.hypot(na['x']-nc['x'],na['y']-nc['y']),2*R,(view,a,c))

    def test_visible_labels_clear_nodes_and_each_other(self):
        for view in ('source','model'):
            v=self.views[view]
            labels=[(i,label_rect(r['label'])) for i,r in v['routes'].items() if not r['label']['crowded']]
            self.assertEqual(len(v['routes'])-len(labels),v['hidden'],view)
            for i,(a,ra) in enumerate(labels):
                for node_id,node in v['nodes'].items(): self.assertFalse(rect_hits_circle(ra,node),(view,a,node_id))
                for c,rc in labels[i+1:]: self.assertFalse(rects_overlap(ra,rc),(view,a,c))

    def test_routes_run_from_source_to_target_boundary(self):
        for view in ('source','model'):
            v=self.views[view]
            for e in v['edges']:
                samples=v['routes'][e['id']]['samples']
                s,t=v['nodes'][e['source']],v['nodes'][e['target']]
                self.assertAlmostEqual(math.hypot(samples[0]['x']-s['x'],samples[0]['y']-s['y']),R,delta=1.5,msg=(view,e['id']))
                self.assertAlmostEqual(math.hypot(samples[-1]['x']-t['x'],samples[-1]['y']-t['y']),R,delta=1.5,msg=(view,e['id']))

    def test_straight_edges_unless_reported_bent(self):
        for v in self.views.values():
            self.assertEqual(sum(1 for r in v['routes'].values() if r['bent']),v['bent'])
            for r in v['routes'].values():
                if not r['bent']: self.assertEqual(len(r['samples']),2)

    def test_source_claims_have_no_crossings(self):
        v=self.views['source']
        self.assertEqual(count_crossings(v),0)
        self.assertEqual(v['crossings'],0)
        for name,view in self.views.items(): self.assertEqual(view['crossings'],count_crossings(view),name)

    def test_source_layout_is_compact(self):
        # Linked circles sit about three radii apart (the reference image: 2.5-3.5), and the canvas is sized to the content.
        v=self.views['source']
        dist=sorted(math.hypot(v['nodes'][e['source']]['x']-v['nodes'][e['target']]['x'],v['nodes'][e['source']]['y']-v['nodes'][e['target']]['y'])/R for e in v['edges'])
        self.assertLessEqual(dist[len(dist)//2],3.6)
        xs=[n['x'] for n in v['nodes'].values()]; ys=[n['y'] for n in v['nodes'].values()]
        self.assertEqual(v['width'],math.ceil(max(xs)+R+MARGIN))
        self.assertEqual(v['height'],math.ceil(max(ys)+R+MARGIN))
        self.assertEqual((min(xs)-R,min(ys)-R),(MARGIN,MARGIN))

    def test_text_is_readable_at_the_fit_scale(self):
        # Fit scale for an 820x700 canvas; node text is 13 px and edge labels 12 px in the viewer.
        # Requested minimums: source node text >= 10 px, source edge labels >= 9 px, model node text >= 6 px.
        for view,node_px,edge_px in (('source',10,9),('model',6,0)):
            v=self.views[view]
            scale=min(1,818/v['width'],698/v['height'])
            self.assertGreaterEqual(13*scale,node_px,view)
            self.assertGreaterEqual(12*scale,edge_px,view)

    def test_unlinked_nodes_are_listed_below_the_graph(self):
        source=self.views['source']
        linked={x for e in source['edges'] for x in (e['source'],e['target'])}
        unlinked=[i for i in source['nodes'] if i not in linked]
        self.assertEqual([i.split('/')[-1] for i in unlinked],['mitral_orifice'])
        lowest=max(source['nodes'][i]['y'] for i in linked)
        self.assertGreater(source['nodes'][unlinked[0]]['y'],lowest+R)
        catalog=self.views['catalog']
        self.assertEqual(len(catalog['nodes']),31)
        self.assertEqual(sorted(g['label'] for g in catalog['groups']),['catalogue','lumped part','modelled','reference'])

    def test_layout_is_deterministic(self):
        self.assertEqual(run_node(RUNNER),self.raw)
