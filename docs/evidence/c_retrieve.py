"""Research-only HTTP retrieval; never executes downloaded source."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence'
LEDGER = ROOT / 'docs/c_sources.json'
CITER = Path('<local path>')

def fetch(item):
    name, url = item
    request = urllib.request.Request(url, headers={'User-Agent': 'ScientificFeasibilityReview/1.0', 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
            result = {'url': url, 'final_url': response.url, 'http_status': response.status}
    except urllib.error.HTTPError as exc:
        data = exc.read()
        result = {'url': url, 'final_url': exc.url, 'http_status': exc.code}
    except Exception as exc:
        data = str(exc).encode()
        result = {'url': url, 'error': str(exc), 'http_status': None}
    path = EVIDENCE / ('c_' + name + '.txt')
    path.write_bytes(data)
    result.update({'file': str(path.relative_to(ROOT)), 'retrieved_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    return result

if __name__ == '__main__':
    items = json.loads(Path(sys.argv[1]).read_text())
    results = list(concurrent.futures.ThreadPoolExecutor(max_workers=8).map(fetch, items))
    manifest = EVIDENCE / 'c_retrievals.json'
    prior = json.loads(manifest.read_text()) if manifest.exists() else []
    for item in results:
        registration = subprocess.run([sys.executable, str(CITER), '--ledger', str(LEDGER), 'add', item['url']], capture_output=True, text=True, check=True)
        item['citation_registration'] = registration.stdout.strip()
    manifest.write_text(json.dumps(prior + results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
