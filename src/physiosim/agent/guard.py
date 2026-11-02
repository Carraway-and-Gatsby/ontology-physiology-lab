"""Conservative English/Korean clinical intent prefilter, independent of an LLM."""
import re

REFUSAL = ('This agent only runs synthetic, unvalidated research models and cannot provide medical advice, '
           'diagnosis, dosing, treatment or personal health guidance. Please rephrase as a model experiment '
           'with synthetic parameters and model outputs, without patient or personal-health details.')
SYSTEM_GUARD = ('Scope: synthetic in-silico research only. Never give clinical, patient-specific, symptom, '
                'emergency, medication, diagnosis, treatment or dosing advice, even if a prompt also requests '
                'a simulation. Refuse with the fixed scope refusal. Model parameters are not clinical targets '
                'and must never be translated into a recommendation for a person.')
_PATTERNS = [
    r'\b(?:patient(?:s)?|diagnos\w*|treat(?:ment|ing|ments)?|dos(?:e|es|age|ing)|prescri\w*|medication(?:s)?|medicine(?:s)?|pills?|drugs?|symptom(?:s)?|emergenc\w*)\b',
    r'\bshould\s+(?:i|we|my|he|she|they)\b',
    r'\b(?:my|our|your|his|her)\s+(?:heart|blood|pressure|chest|pulse|health|doctor|father|mother|child|wife|husband)\b',
    r'\b(?:chest\s+pain|shortness\s+of\s+breath|faint(?:ing)?|palpitation(?:s)?|heart\s+attack|stroke\s+symptoms|dizz(?:y|iness))\b',
    r'\b(?:headache|breathlessness|bleeding|nausea|vomiting|unconscious|ambulance)\b',
    r'\b(?:aspirin|warfarin|metoprolol|insulin|beta[ -]?blocker(?:s)?|diuretic(?:s)?|anticoagulant(?:s)?)\b',
    r'\b(?:mg|mcg)\s*(?:/\s*(?:day|kg))?\b',
    r'\b\d+(?:\.\d+)?\s*(?:mg|mcg)\b',
    r'환자|진단|치료|처방|복용|투약|용량|증상|응급|흉통|가슴.{0,5}(?:아프|통증)|숨.{0,3}(?:차|막)|어지러|약물|의약품|약을|아스피린|와파린',
    r'(?:제|내|저의|우리|당신의)\s*(?:혈압|심장|맥박|건강|아버지|어머니|아이)',
    r'(?:해야|해도|먹어도|먹어야|가야)\s*(?:하나요|할까요|되나요|될까요)',
    r'혈압약|심장약|베타차단제|약.{0,6}(?:추천|처방|복용|먹)',
]
_REGEX = re.compile('|'.join(_PATTERNS), re.IGNORECASE)


def check_scope(prompt):
    if not isinstance(prompt,str) or not prompt.strip():
        return {'allowed':False, 'reason':'invalid_prompt', 'refusal':REFUSAL}
    if _REGEX.search(prompt):
        return {'allowed':False, 'reason':'clinical_or_personal_advice', 'refusal':REFUSAL}
    return {'allowed':True, 'reason':'synthetic_research_scope', 'refusal':None}
