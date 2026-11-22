"""Opt-in domain-mask repair; legacy prepare remains frozen for original results."""
import re
from functools import lru_cache
from pathlib import Path
from .preprocessing import EMAIL,PHONE,LONG_NUMBER,normalized,prepare

@lru_cache(maxsize=1)
def url_pattern():
    path=Path(__file__).resolve().parents[2]/'data/reference/iana-tlds.txt'
    tlds=[line.strip().lower() for line in path.read_text(encoding='ascii').splitlines() if line.strip() and not line.startswith('#')]
    if len(tlds)<100:raise ValueError('Incomplete IANA snapshot; cannot silently fall back to a short suffix list.')
    suffixes='|'.join(re.escape(t) for t in sorted(tlds,key=lambda t:(-len(t),t)))
    label=r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    domain=rf'(?<![\w@])(?:{label}\.)+(?:{suffixes})(?![a-z0-9-])(?:[/?#][^\s<>]*)?'
    return re.compile(r'(?:https?://|www\.)[^\s<>]+|'+domain,re.I)

def mask_contacts_v2(text):
    text=EMAIL.sub(' EMAILTOKEN ',normalized(text))
    text=url_pattern().sub(' URLTOKEN ',text)
    text=PHONE.sub(lambda m:' PHONETOKEN ' if sum(c.isdigit() for c in m[0])>=7 else m[0],text)
    return ' '.join(LONG_NUMBER.sub(' NUMBERTOKEN ',text).split())

def prepare_v2(text):
    record=prepare(text)  # Reuse validation and the unchanged non-URL structure.
    without_emails=EMAIL.sub(' EMAILTOKEN ',normalized(text))
    record['structural'][4]=min(len(list(url_pattern().finditer(without_emails))),5)/5
    record['text']=mask_contacts_v2(text).lower()
    return record
