"""Generic LLM fallback chain: Gemini (Google AI Studio) -> Groq ->
OpenRouter, each wrapped so a bad key, an exhausted quota, a timeout, or
a malformed response just falls through to the next provider rather
than raising. If all three fail (or none are configured - see
config.settings' GEMINI_API_KEY/GROQ_API_KEY/OPENROUTER_API_KEY),
`ask_json()` returns None and the caller keeps its own fallback
behaviour.

Every provider is asked for the exact same structured JSON, via a
caller-supplied prompt/system_prompt/required_keys, so the caller
doesn't need to know which one actually answered. First consumer: song
genre/mood classification (backend.music_app.shared_utils.
song_classification) - kept generic here so a later feature (e.g. a
natural-language search) can reuse the same chain with its own prompt.
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 45  # seconds


def _strip_code_fence(raw):
    """Some models wrap JSON in ```json ... ``` even when told not to."""
    text = (raw or '').strip()
    match = re.match(r'^```(?:json)?\s*(.*?)\s*```$', text, re.DOTALL)
    return match.group(1) if match else text


def _call_gemini(prompt, system_prompt):
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None
    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'gemini-flash-latest:generateContent?key={api_key}'
    )
    resp = requests.post(url, json={
        'system_instruction': {'parts': [{'text': system_prompt}]},
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.4, 'response_mime_type': 'application/json'},
    }, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data['candidates'][0]['content']['parts'][0]['text']


def _call_openai_compatible(url, api_key, model, prompt, system_prompt):
    """Shared shape for Groq and OpenRouter - both speak the OpenAI chat API."""
    if not api_key:
        return None
    resp = requests.post(
        url,
        headers={'Authorization': f'Bearer {api_key}'},
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.4,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def _call_groq(prompt, system_prompt):
    return _call_openai_compatible(
        'https://api.groq.com/openai/v1/chat/completions',
        settings.GROQ_API_KEY, 'openai/gpt-oss-120b', prompt, system_prompt,
    )


def _call_openrouter(prompt, system_prompt):
    return _call_openai_compatible(
        'https://openrouter.ai/api/v1/chat/completions',
        settings.OPENROUTER_API_KEY, 'google/gemma-4-31b-it:free', prompt, system_prompt,
    )


# Tried in this order; each entry is (name, callable(prompt, system_prompt) -> raw_text|None).
_PROVIDERS = [
    ('gemini', _call_gemini),
    ('groq', _call_groq),
    ('openrouter', _call_openrouter),
]


def ask_json(prompt, system_prompt, required_keys=()):
    """Tries each provider in order; returns the first valid parsed JSON
    dict containing every key in `required_keys`, or None if every
    provider failed, returned unusable output, or none are configured.
    """
    for name, call in _PROVIDERS:
        try:
            raw = call(prompt, system_prompt)
        except Exception:
            logger.exception('[llm_providers] %s call failed, trying next provider', name)
            continue

        if not raw:
            continue

        text = _strip_code_fence(raw)
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            logger.warning('[llm_providers] %s returned non-JSON, trying next provider: %.200s', name, text)
            continue

        if not isinstance(data, dict) or not all(k in data for k in required_keys):
            logger.warning('[llm_providers] %s JSON missing required keys, trying next provider: %.200s', name, text)
            continue

        return data

    return None
