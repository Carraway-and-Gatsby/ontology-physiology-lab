"""Geometry checks for the viewer's layered layout, run under node on the frozen inputs."""
import json, pathlib, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import build_graph as b
ROOT=pathlib.Path(__file__).resolve().parents[1]
NODE=shutil.which('node')
LV_WALL_TO_LV='rel-d4fc71cd7059c217'
LV_CAVITY='https://example.org/physiosim/anatomical-contents#heart/lv_cavity'
RUNNER="""
const GraphLayout=require(process.argv[2]);
const data=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const out={};
for(const view of ['source','model','catalog']){
  const {nodes,edges}=GraphLayout.viewSubset(data,view);
  const layout=GraphLayout.layoutGraph(nodes,edges,{groupOf:view==='catalog'?n=>n.record.node_class:null});
  out[view]={width:layout.width,height:layout.height,crossings:layout.crossings,groups:layout.groups,
    nodes:Object.fromEntries(layout.nodes),
    routes:Object.fromEntries([...layout.routes].map(([id,r])=>[id,{samples:r.samples,label:r.label}])),
    edges:edges.map(e=>({id:e.id,source:e.source,target:e.target}))};
}
process.stdout.write(JSON.stringify(out));
"""

def run_layout():
    html=(ROOT/'viewer.html').read_text(encoding='utf-8')
    script=html.split('<script id="graph-layout">',1)[1].split('</script>',1)[0]
    with tempfile.TemporaryDirectory() as temp:
        temp=pathlib.Path(temp)
        (temp/'layout.js').write_text(script,encoding='utf-8')
        (temp/'runner.js').write_text(RUNNER,encoding='utf-8')
        (temp/'graph.json').write_text(json.dumps(b.build_graph(ROOT/'inputs')),encoding='utf-8')
        return subprocess.run([NODE,str(temp/'runner.js'),str(temp/'layout.js'),str(temp/'graph.json')],check=True,capture_output=True,text=True).stdout

def rect(box,pad=0):
    return (box['x']-box['w']/2-pad,box['y']-box['h']/2-pad,box['x']+box['w']/2+pad,box['y']+box['h']/2+pad)

def inside(point,r):
    return r[0]<point['x']<r[2] and r[1]<point['y']<r[3]

def overlap(a,c):
    return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]

@unittest.skipUnless(NODE,'node is required to run the viewer layout')
class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=run_layout(); cls.views=json.loads(cls.raw)

    def test_routes_clear_every_unrelated_node(self):
        for view in ('source','model'):
            v=self.views[view]
            for e in v['edges']:
                for node_id,box in v['nodes'].items():
                    if node_id in (e['source'],e['target']): continue
                    r=rect(box,-1)
                    self.assertFalse(any(inside(p,r) for p in v['routes'][e['id']]['samples']),(view,e['id'],node_id))

    def test_reported_lv_wall_edge_clears_lv_cavity(self):
        v=self.views['source']
        r=rect(v['nodes'][LV_CAVITY],-1)
        self.assertFalse(any(inside(p,r) for p in v['routes'][LV_WALL_TO_LV]['samples']))
        label=v['routes'][LV_WALL_TO_LV]['label']
        self.assertFalse(label['crowded'])
        self.assertFalse(overlap(rect(label),rect(v['nodes'][LV_CAVITY])))

    def test_nodes_do_not_overlap(self):
        for view,v in self.views.items():
            boxes=list(v['nodes'].items())
            for i,(a,box_a) in enumerate(boxes):
                for c,box_c in boxes[i+1:]:
                    self.assertFalse(overlap(rect(box_a),rect(box_c)),(view,a,c))

    def test_visible_labels_clear_nodes_and_each_other(self):
        self.assertFalse(any(r['label']['crowded'] for r in self.views['source']['routes'].values()))
        for view in ('source','model'):
            v=self.views[view]
            labels=[(i,rect(r['label'])) for i,r in v['routes'].items() if not r['label']['crowded']]
            for i,(a,ra) in enumerate(labels):
                for node_id,box in v['nodes'].items(): self.assertFalse(overlap(ra,rect(box)),(view,a,node_id))
                for c,rc in labels[i+1:]: self.assertFalse(overlap(ra,rc),(view,a,c))

    def test_routes_run_from_source_to_target(self):
        for view in ('source','model'):
            v=self.views[view]
            for e in v['edges']:
                samples=v['routes'][e['id']]['samples']
                self.assertTrue(inside(samples[0],rect(v['nodes'][e['source']],1)),(view,e['id']))
                self.assertTrue(inside(samples[-1],rect(v['nodes'][e['target']],1)),(view,e['id']))

    def test_source_claims_point_up_without_crossings(self):
        v=self.views['source']
        self.assertEqual(v['crossings'],0)
        for e in v['edges']:
            self.assertLess(v['nodes'][e['target']]['y'],v['nodes'][e['source']]['y'],e['id'])

    def test_unlinked_nodes_are_listed_below_the_graph(self):
        source=self.views['source']
        linked={x for e in source['edges'] for x in (e['source'],e['target'])}
        unlinked=[i for i in source['nodes'] if i not in linked]
        self.assertEqual([i.split('/')[-1] for i in unlinked],['mitral_orifice'])
        lowest=max(source['nodes'][i]['y'] for i in linked)
        self.assertGreater(source['nodes'][unlinked[0]]['y'],lowest)
        catalog=self.views['catalog']
        self.assertEqual(len(catalog['nodes']),31)
        self.assertEqual(sorted(g['label'] for g in catalog['groups']),['catalogue','lumped part','modelled','reference'])

    def test_layout_is_deterministic(self):
        self.assertEqual(run_layout(),self.raw)
