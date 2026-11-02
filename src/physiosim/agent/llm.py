"""Minimal OpenAI-compatible tool-calling client using urllib only.

No credential discovery/network activity happens at import or in FakeProvider.
"""
from dataclasses import dataclass, field
import json
import os
import re
import time
from urllib import request, error, parse


class ProviderError(RuntimeError):
    pass


def redact(text, secrets=()):
    text = str(text)
    for secret in secrets:
        if secret:
            text = text.replace(secret,'[REDACTED]')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;"}]+',r'\1[REDACTED]',text)
    return text


@dataclass(frozen=True, repr=False)
class ProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.
    retries: int = 2
    extra: dict = field(default_factory=dict)

    def __repr__(self):
        return f'ProviderConfig(provider={self.provider!r}, model={self.model!r}, api_key=[REDACTED])'


def parse_extra_json(value):
    """Parse request extensions without reflecting possibly sensitive input."""
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError('object required')
        json.dumps(parsed, allow_nan=False)
    except (ValueError, TypeError):
        raise ProviderError('extra request fields must be a finite JSON object') from None
    return parsed


CLASSIFIER_MAX_TOKENS = {'meta': 1500}


def provider_config(provider='meta', model=None, environ=None, *, extra=None):
    env = os.environ if environ is None else environ
    presets = {'meta':('https://api.meta.ai/v1','MODEL_API_KEY','muse-spark-1.3'),
               'openai':('https://api.openai.com/v1','OPENAI_API_KEY',None),
               'anthropic':('https://api.anthropic.com/v1','ANTHROPIC_API_KEY',None),
               'custom':(env.get('LAB_LLM_BASE_URL',''),'LAB_LLM_API_KEY',None)}
    if provider not in presets:
        raise ProviderError('provider must be meta, openai, anthropic or custom')
    base, key_env, default_model = presets[provider]
    selected = model or (default_model if provider == 'meta' else env.get('LAB_LLM_MODEL'))
    if not selected:
        raise ProviderError('set --model or LAB_LLM_MODEL for this provider')
    key = env.get(key_env,'')
    if not key and provider != 'custom':
        raise ProviderError('missing credential environment variable '+key_env)
    parsed = parse.urlsplit(base)
    if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderError('base URL must be an http(s) endpoint without credentials, query or fragment')
    if parsed.scheme == 'http' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ProviderError('plain HTTP is supported only for loopback custom providers')
    # OpenAI GPT-6.x needs reasoning_effort none for chat-completions tool use; Meta Muse Spark does not accept
    # 'none' (minimal..xhigh) and spends completion tokens on reasoning, so default it to 'low'.
    fields = {'reasoning_effort':'none'} if provider == 'openai' else {'reasoning_effort':'low'} if provider == 'meta' else {}
    if 'LAB_LLM_EXTRA_JSON' in env:
        fields.update(parse_extra_json(env['LAB_LLM_EXTRA_JSON']))
    if extra is not None:
        if not isinstance(extra,dict):
            raise ProviderError('extra request fields must be a finite JSON object')
        try:
            fields.update(parse_extra_json(json.dumps(extra,allow_nan=False)))
        except (ValueError,TypeError):
            raise ProviderError('extra request fields must be a finite JSON object') from None
    return ProviderConfig(provider,base.rstrip('/'),key,selected,extra=fields)


def _error_excerpt(response, api_key):
    """Use only the body, redact before clipping, and bound both reads and output."""
    try:
        raw = response.read(8*1024*1024+1)
        if len(raw) > 8*1024*1024:
            return 'error response exceeded size limit'
        body = raw.decode('utf-8',errors='replace')
        try:
            data = json.loads(body)
            message = data.get('error',{}).get('message') if isinstance(data,dict) else None
            if isinstance(message,str):
                body = message
        except (ValueError,AttributeError):
            pass
        return redact(body,(api_key,))[:600]
    except (OSError,ValueError):
        return 'error response body unavailable'


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward bearer credentials to an unexpected host.
        return None


class ChatProvider:
    def __init__(self, config, *, opener=None, sleeper=time.sleep):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self._opener = opener if opener is not None else request.build_opener(_NoRedirect()).open
        self._sleep = sleeper

    def complete(self, messages, tools, *, deadline=None, tool_choice='auto'):
        config = self.config
        fields = {**config.extra,'model':config.model,'messages':messages}
        token_field = 'max_completion_tokens' if config.provider == 'openai' else 'max_tokens'
        other_field = 'max_tokens' if token_field == 'max_completion_tokens' else 'max_completion_tokens'
        if other_field in fields:
            fields.setdefault(token_field,fields.pop(other_field))
        if tools and tool_choice != 'none':
            fields.update(tools=tools,tool_choice='auto')
        elif messages and messages[0].get('content','').startswith('SCOPE_CLASSIFIER.'):
            # Scope calls alone receive the classifier schema and short token cap.
            fields.update(response_format={'type':'json_schema','json_schema':{'name':'scope_decision','strict':True,
                'schema':{'type':'object','properties':{'in_scope':{'type':'boolean'},'reason':{'type':'string'}},
                          'required':['in_scope','reason'],'additionalProperties':False}}})
            fields.pop('max_tokens',None); fields.pop('max_completion_tokens',None)
            # Reasoning models (Meta Muse Spark) count reasoning tokens against this cap: measured 380-440
            # reasoning tokens at effort 'low' for one classifier call, so 200 truncates to empty content.
            fields[token_field] = CLASSIFIER_MAX_TOKENS.get(config.provider, 200)
            fields.pop('tools',None); fields.pop('tool_choice',None)
        else:
            # Forced final/repair calls retain the normal completion budget.
            fields.update(response_format={'type':'json_schema','json_schema':{'name':'final_message','strict':True,
                'schema':{'type':'object','properties':{'model':{'type':'string','enum':['phase1','m1']},
                    'findings':{'type':'array','items':{'type':'object','properties':{
                        'run_id':{'type':'string'},'metric_path':{'type':'string'}},
                        'required':['run_id','metric_path'],'additionalProperties':False}}},
                    'required':['model','findings'],'additionalProperties':False}}})
            fields.pop('tools',None); fields.pop('tool_choice',None)
        if tools:
            # Tool history requires schemas even when further calls are disabled.
            fields.update(tools=tools,tool_choice=tool_choice)
        headers = {'Content-Type':'application/json','Accept':'application/json'}
        if config.api_key:
            headers['Authorization'] = 'Bearer '+config.api_key
        format_retry = False
        token_retry = False
        attempt = 0
        while True:
            if deadline is not None:
                deadline.check()
            req = request.Request(config.base_url+'/chat/completions',
                data=json.dumps(fields,allow_nan=False).encode(),headers=headers,method='POST')
            try:
                with self._opener(req,timeout=config.timeout if deadline is None else deadline.timeout(config.timeout)) as response:
                    raw = response.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise ProviderError('provider response exceeded size limit')
                data = json.loads(raw)
                message = data['choices'][0]['message']
                if not isinstance(message,dict):
                    raise ValueError('invalid assistant message')
                return {'message':message,'usage':data.get('usage') or {}}
            except error.HTTPError as exc:
                status = exc.code
                try:
                    excerpt = _error_excerpt(exc,config.api_key)
                finally:
                    exc.close()
                if status == 400 and not token_retry and any(
                        field in excerpt.casefold() for field in ('max_tokens','max_completion_tokens')):
                    current = next((field for field in ('max_tokens','max_completion_tokens') if field in fields),None)
                    if current is not None:
                        other = 'max_completion_tokens' if current == 'max_tokens' else 'max_tokens'
                        fields[other] = fields.pop(current)
                        token_retry = True
                        continue
                if 'response_format' in fields and not format_retry and status in (400,422) and 'response_format' in excerpt.casefold() and any(
                        word in excerpt.casefold() for word in ('unsupported','not supported','unrecognized','unknown','not allowed')):
                    fields.pop('response_format',None)
                    format_retry = True
                    continue
                if (status == 429 or 500 <= status < 600) and attempt < config.retries:
                    self._sleep(min(2**attempt,8) if deadline is None else min(2**attempt,8,deadline.remaining()))
                    attempt += 1
                    continue
                raise ProviderError(f'provider HTTP {status}: {excerpt}') from None
            except (error.URLError, TimeoutError, OSError):
                if attempt < config.retries:
                    self._sleep(min(2**attempt,8) if deadline is None else min(2**attempt,8,deadline.remaining()))
                    attempt += 1
                    continue
                raise ProviderError('provider transport error or timeout; Authorization: [REDACTED]') from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise ProviderError('invalid provider JSON response; Authorization: [REDACTED]') from None


class FakeProvider:
    """Scripted test provider. Each response is a message or a callable(messages).

    FakeProvider.for_experiment() demonstrates tools with actual engine outputs;
    its parameter mapping is supplied explicitly, never used to score LLM quality.
    """
    provider = 'fake'
    model = 'scripted-offline'

    def __init__(self, responses, *, classifier_answers=None):
        self.responses = iter(responses)
        self.classifier_answers = iter(classifier_answers) if classifier_answers is not None else None
        self.calls = 0
        self.classifier_calls = 0
        self.requests = []

    def complete(self, messages, tools, *, deadline=None, tool_choice='auto'):
        from copy import deepcopy
        self.requests.append(deepcopy({'messages':messages,'tools':tools,'tool_choice':tool_choice}))
        self.calls += 1
        if not tools and messages and messages[0].get('content','').startswith('SCOPE_CLASSIFIER.'):
            from .guard import check_scope, classifier_hypothesis
            self.classifier_calls += 1
            try:
                item = next(self.classifier_answers) if self.classifier_answers is not None else {
                    'in_scope':check_scope(classifier_hypothesis(messages))['allowed'],'reason':'offline scripted scope decision'}
            except StopIteration:
                raise ProviderError('FakeProvider classifier script exhausted') from None
            if isinstance(item,Exception):
                raise item
            item = item(messages) if callable(item) else item
            message = item if isinstance(item,dict) and 'content' in item else {'role':'assistant','content':json.dumps(item)}
            return {'message':message,'usage':{}}
        try:
            item = next(self.responses)
        except StopIteration:
            raise ProviderError('FakeProvider script exhausted') from None
        if isinstance(item,Exception):
            raise item
        message = item(messages) if callable(item) else item
        return {'message':message,'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}}

    @classmethod
    def for_experiment(cls, model='m1', intervention=None, *, metric='stroke_volume_ml', cycles=None):
        intervention = {'resistance_mitral':{'scale':3}} if intervention is None else intervention
        parameter = next(iter(intervention), 'heart_rate')
        def call(name,args,index):
            return {'id':'fake-tool-'+str(index),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}
        first = {'role':'assistant','content':'Inspect the local parameter and evidence contracts.',
                 'tool_calls':[call('list_parameters',{'model':model},0),
                               call('lookup_ontology',{'query':parameter},1),
                               call('get_evidence',{'entity_or_param':parameter},2)]}
        arguments = {'model':model,'intervention':intervention}
        if cycles is not None:
            arguments['cycles'] = cycles
        second = {'role':'assistant','content':'Compare synthetic baseline and intervention using the real engine.',
                  'tool_calls':[call('run_experiment',arguments,3)]}
        def final(messages):
            results = [json.loads(m['content']) for m in messages if m.get('role') == 'tool' and m.get('name') == 'run_experiment']
            results = [r for r in results if 'run_id' in r]
            if not results:
                raise ProviderError('offline experiment script received an engine error')
            return {'role':'assistant','content':json.dumps({'model':model,'findings':[
                {'run_id':r['run_id'],'metric_path':prefix+metric} for r in results
                for prefix in ('baseline.metrics.','intervention.metrics.','delta.abs.')]})}

        return cls([first,second,final])
