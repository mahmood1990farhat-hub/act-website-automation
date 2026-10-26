"""Public, read-only description of the exact server-selected checkout terms.

No draft release is supplied here. The existing capture service remains the final
pre-payment authority; discovery is not acceptance and never creates a record.
"""
import hashlib
import re
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.trips.services.cancellation_policy import CANDIDATE_POLICY_VERSION, _utc

LOCALES = frozenset(('en', 'ar', 'fr', 'de', 'es', 'tr', 'zh'))
HASH = re.compile(r'[0-9a-f]{64}')
PDF_PATH = re.compile(r'/documents/[A-Za-z0-9/_-]+\.pdf')


def public_checkout_terms(locale, now):
    """Allowlist public content only. Never return arbitrary release configuration.

    Text is verified against its configured SHA. The PDF digest is a release
    assertion, NOT proof that the public URL currently serves those bytes.
    Publication/deployment must separately verify the actual PDF and translations.
    """
    enabled = getattr(settings, 'ACT_BOOKING_TERMS_CHECKOUT_ENABLED', False)
    if type(enabled) is not bool:
        raise ValueError('Invalid terms activation configuration')
    if not enabled:
        return {'schema': 1, 'enabled': False}
    if locale not in LOCALES:
        raise ValueError('Unsupported document language')
    release = getattr(settings, 'ACT_BOOKING_TERMS_RELEASE', None)
    if not isinstance(release, dict) or release.get('published') is not True:
        raise ValueError('No published release')
    if release.get('policy_version') != CANDIDATE_POLICY_VERSION:
        raise ValueError('Unsupported policy')
    effective = _utc(datetime.fromisoformat(release['effective_at']), 'effective_at')
    if _utc(now, 'now') < effective:
        raise ValueError('Release is not effective')
    version = release.get('terms_version')
    if not isinstance(version, str) or not 1 <= len(version.strip()) <= 120 or '\n' in version or '\r' in version:
        raise ValueError('Invalid document version')
    locales = release.get('locales')
    doc = locales.get(locale) if isinstance(locales, dict) else None
    if not isinstance(doc, dict):
        raise ValueError('No reviewed document for requested language')
    text = doc.get('text')
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 262144:
        raise ValueError('Invalid reviewed document')
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if doc.get('sha256') != text_hash:
        raise ValueError('Document hash mismatch')
    pdf_hash, path = doc.get('pdf_sha256'), doc.get('url')
    if not isinstance(pdf_hash, str) or HASH.fullmatch(pdf_hash) is None:
        raise ValueError('Invalid PDF hash')
    if not isinstance(path, str) or PDF_PATH.fullmatch(path) is None or '//' in path:
        raise ValueError('Invalid document path')
    return {'schema': 1, 'enabled': True, 'terms_version': version,
            'terms_sha256': text_hash, 'locale': locale, 'text': text,
            'document_url': path, 'pdf_sha256': pdf_hash,
            'effective_at': effective.isoformat()}


@never_cache
@require_GET
def checkout_terms_view(request):
    """No auth/PI identifier needed to read public terms. Reject silent fallback."""
    if set(request.GET) != {'locale'} or len(request.GET.getlist('locale')) != 1 or request.GET['locale'] not in LOCALES:
        return JsonResponse({'schema': 1, 'error': 'invalid_locale'}, status=400)
    try:
        data = public_checkout_terms(request.GET['locale'], timezone.now())
    except (ValueError, TypeError, KeyError, OverflowError):
        # Do not leak internal configuration, exception details, or draft text.
        return JsonResponse({'schema': 1, 'error': 'terms_unavailable'}, status=503)
    return JsonResponse(data)
