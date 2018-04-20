# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect

from kuma.core.decorators import shared_cache_control

from ..models import Document, Revision


# Legacy MindTouch redirects.

MINDTOUCH_NAMESPACES = (
    'Help',
    'Help_talk',
    'Project',
    'Project_talk',
    'Special',
    'Talk',
    'Template',
    'Template_talk',
    'User',
)


def mindtouch_namespace_redirect(request, namespace, slug):
    """
    For URLs in special namespaces (like Talk:, User:, etc.), redirect
    if possible to the appropriate new URL in the appropriate
    locale. If the locale cannot be correctly determined, fall back to
    en-US.
    """
    new_locale = new_slug = None
    if namespace in ('Talk', 'Project', 'Project_talk'):
        # These namespaces carry the old locale in their URL, which
        # simplifies figuring out where to send them.
        locale, _, doc_slug = slug.partition('/')
        new_locale = settings.MT_TO_KUMA_LOCALE_MAP.get(locale, 'en-US')
        new_slug = '%s:%s' % (namespace, doc_slug)
    elif namespace == 'User':
        # For users, we look up the latest revision and get the locale
        # from there.
        new_slug = '%s:%s' % (namespace, slug)
        try:
            rev = (Revision.objects.filter(document__slug=new_slug)
                                   .latest('created'))
            new_locale = rev.document.locale
        except Revision.DoesNotExist:
            # If that doesn't work, bail out to en-US.
            new_locale = 'en-US'
    else:
        # Templates, etc. don't actually have a locale, so we give
        # them the default.
        new_locale = 'en-US'
        new_slug = '%s:%s' % (namespace, slug)
    if new_locale:
        new_url = '/%s/docs/%s' % (request.LANGUAGE_CODE, new_slug)
    return redirect(new_url, permanent=True)


@shared_cache_control(s_maxage=60 * 60 * 24 * 30)
def mindtouch_to_kuma_redirect(request, path):
    """
    Given a request to a Mindtouch-generated URL, generate a redirect
    to the correct corresponding kuma URL.
    """
    locale = request.LANGUAGE_CODE
    if path.startswith('%s/' % locale):
        # Convert from Django-based LocaleMiddleware path to zamboni/amo style
        path = path.replace('%s/' % locale, '', 1)

    if path.startswith('Template:MindTouch'):
        # MindTouch's default templates. There shouldn't be links to
        # them anywhere in the wild, but just in case we 404 them.
        raise Http404

    if path.endswith('/'):
        # If there's a trailing slash, snip it off.
        path = path[:-1]

    if ':' in path:
        namespace, _, slug = path.partition(':')
        # The namespaces (Talk:, User:, etc.) get their own
        # special-case handling.
        if namespace in MINDTOUCH_NAMESPACES:
            return mindtouch_namespace_redirect(request, namespace, slug)

    # Last attempt: we try the request locale as the document locale,
    # and see if that matches something.
    try:
        doc = Document.objects.get(slug=path, locale=locale)
    except Document.DoesNotExist:
        raise Http404

    location = doc.get_absolute_url()
    if 'view' in request.GET:
        location = '%s$%s' % (location, request.GET['view'])

    return redirect(location, permanent=True)
