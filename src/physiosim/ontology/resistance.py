"""D-RES: traversed segment context, with no per-segment numeric bindings."""
import json
from importlib.resources import files


def resistance_details():
    data=json.loads(files(__package__).joinpath('resistance_evidence.json').read_text())
    terms=data['terms']
    beds={
        'systemic':['UBERON:0004573',None,'UBERON:0001980','UBERON:0001982','UBERON:0001979','UBERON:0013140'],
        'pulmonary':['UBERON:0002012','UBERON:8600077','UBERON:0016405','UBERON:8600024','UBERON:0002016']}
    result={}
    for bed,ids in beds.items():
        segments=[]
        for identifier in ids:
            if identifier is None:
                segments.append({'key':'local:small_arteries','term_id':None,'label':'small arteries',
                                 'iri':None,'fma_xrefs':[],'status':'unknown','relation':'traverses',
                                 'note':'No exact identifier established; muscular artery is not asserted equivalent.'})
            else:
                t=terms[identifier]
                segments.append({'key':identifier,'term_id':identifier,'label':t['label'],'iri':t['iri'],
                                 'fma_xrefs':t['fma_xrefs'],'status':'context','relation':'traverses',
                                 'evidence':{'source_id':t['source_id'],'url':t['url'],'sha256':t['sha256'],
                                             'excerpt_file':'docs/evidence/resistance/terms.json'}})
        names={'PMC10110735','PMID3946629','PMC6039797'} if bed=='systemic' else {'PMC10110735','PMC297229','PMC6039797'}
        evidence=[{'source_id':s['source_id'],'url':s['url'],'sha256':s['sha256'],'excerpt_file':s['excerpt_file']}
                  for s in data['sources'] if s['source_id'].split(':')[-1] in names]
        result[bed]={'relation':'traverses','numeric_binding':'NONE','note':data['notes'][bed],
                     'segments':segments,'evidence':evidence,
                     'scope':'Annotation only; the path retains one model resistance, not segment-specific values.'}
    return result
