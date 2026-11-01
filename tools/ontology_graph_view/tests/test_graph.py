import unittest, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import build_graph as b
P=pathlib.Path(__file__).resolve().parents[1]/'inputs'
S=json.loads((P/'applied_sidecar.json').read_text())
C=json.loads((P/'anatomy_nodes_v2.json').read_text())

class GraphTests(unittest.TestCase):
    def test_identity(self):
        n=b.source_nodes(S)
        self.assertEqual({x["id"] for x in n}, {x["record"]["template_uri"] for x in S["source"]["catalog"]})
        self.assertEqual(n[0]["record"],S["source"]["catalog"][0]["record"])
    def test_claims(self):
        edges=b.source_edges(S)
        self.assertEqual(len(edges),12)
        for e,x in zip(edges,S["source"]["claims"]):
            r=x["record"]
            self.assertEqual((e["source"],e["target"],e["predicate"],e["claim_id"],e["record"],e["provenance"]),(r["sourceTemplate"],r["targetTemplate"],r["relation"],r["claim_id"],r,x["provenance"]))
    def test_blood(self):
        blood=[x for x in b.source_nodes(S) if x["record"]["base_id"]=="UBERON:0000178"]
        self.assertEqual(len(blood),2)
        self.assertEqual(len({x["id"] for x in blood}),2)
        self.assertEqual(len(b.catalog_nodes(C)),31)
    def test_dependency(self):
        edges=b.dependency_edges(S)
        self.assertTrue(any(x["source"]=="model:heart_rate" and x["target"]=="model:activation" for x in edges))
        self.assertTrue(all(x["layer"]=="model_reference" for x in edges))
    def test_escaping(self):
        encoded=b.encode({"label":"</script><img onerror=alert(1)>"})
        self.assertNotIn("<",encoded)
        self.assertEqual(json.loads(encoded)["label"],"</script><img onerror=alert(1)>")
    def test_integrity(self):
        self.assertTrue(b.valid(b.source_nodes(S),b.source_edges(S)))
        self.assertFalse(b.valid([{"id":"x"},{"id":"x"}],[]))
        self.assertFalse(b.valid([{"id":"x"}],[{"id":"e","source":"x","target":"missing"}]))

class BuildTests(unittest.TestCase):
    def test_determinism_and_embed(self):
        import tempfile, subprocess
        with tempfile.TemporaryDirectory() as temp:
            outputs=[]
            for n in ('one','two'):
                out=pathlib.Path(temp)/n
                subprocess.run([sys.executable,str(P.parent/'build_graph.py'),'--input-dir',str(P),'--output-dir',str(out)],check=True)
                outputs.append(((out/'index.html').read_bytes(),(out/'graph-data.json').read_bytes()))
            self.assertEqual(outputs[0],outputs[1])
            html,raw=outputs[0]
            embedded=html.split(b'<script id="graph-data" type="application/json">',1)[1].split(b'</script>',1)[0]
            self.assertEqual(json.loads(embedded),json.loads(raw))
    def test_offline_controls_and_safe_inspector(self):
        html=(P.parent/'viewer.html').read_text()
        for name in ('view-source','view-model','view-catalog','search','relation','zoom-in','zoom-out','fit','download','inspector'):
            self.assertIn('id="'+name+'"',html)
        self.assertNotIn('innerHTML',html)
        self.assertIn('pre.textContent=JSON.stringify(item',html)
        self.assertNotIn('<script src=',html)
        self.assertNotIn('<link ',html)
