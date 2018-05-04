import threading

from django.conf import settings
from django.core.urlresolvers import reverse as django_reverse
from django.test.client import RequestFactory
from django.utils import translation
from django.utils.translation.trans_real import parse_accept_lang_header


# Thread-local storage for URL prefixes. Access with (get|set)_url_prefix.
_locals = threading.local()


def get_best_language(accept_lang):
    """Given an Accept-Language header, return the best-matching language."""

    ranked = parse_accept_lang_header(accept_lang)
    return find_supported(ranked)


def set_url_prefixer(prefixer):
    """Set the Prefixer for the current thread."""
    _locals.prefixer = prefixer


def reset_url_prefixer():
    """Set the Prefixer for the current thread."""
    global _locals
    _locals = threading.local()


def get_url_prefixer():
    """Get the Prefixer for the current thread, or None."""
    return getattr(_locals, 'prefixer', None)


def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None,
            current_app=None, force_locale=False, locale=None, unprefixed=False):
    """Wraps Django's reverse to prepend the requested locale.

    Keyword Arguments:
    * locale - Use this locale prefix rather than the current active locale.

    Keyword Arguments passed to Django's reverse:
    * viewname
    * urlconf
    * args
    * kwargs
    * current_app

    Legacy Keyword Arguments (TODO: remove from callers)
    * prefix
    * force_locale
    * unprefixed
    """
    if locale:
        with translation.override(locale):
            return django_reverse(viewname, urlconf=urlconf, args=args,
                                  kwargs=kwargs, current_app=current_app)
    else:
        return django_reverse(viewname, urlconf=urlconf, args=args,
                              kwargs=kwargs, current_app=current_app)


def find_supported(ranked):
    """Given a ranked language list, return the best-matching locale."""
    langs = dict(settings.LANGUAGE_URL_MAP)
    for lang, _ in ranked:
        lang = lang.lower()
        if lang in langs:
            return langs[lang]
        # Add derived language tags to the end of the list as a fallback.
        pre = '-'.join(lang.split('-')[0:-1])
        if pre:
            ranked.append((pre, None))
    # Couldn't find any acceptable locale.
    return False


def split_path(path):
    """
    Split the requested path into (locale, path).

    locale will be empty if it isn't found.
    """
    path = path.lstrip('/')

    # Use partition instead of split since it always returns 3 parts
    first, _, rest = path.partition('/')

    # Treat locale as a single-item ranked list.
    lang = find_supported([(first, 1.0)])

    if lang:
        return lang, rest
    else:
        return '', path


class Prefixer(object):
    def __init__(self, request=None, locale=None):
        """If request is omitted, fall back to a default locale."""
        self.request = request or RequestFactory(REQUEST_METHOD='bogus').request()
        path_locale, self.shortened_path = split_path(self.request.path_info)

        # Set Self locale according to priority.
        self.locale = locale or path_locale or self.get_chosen_language() or ""

    def get_language(self):
        """
        Return a locale code we support on the site using the
        user's Accept-Language header to determine which is best. This
        mostly follows the RFCs but read bug 439568 for details.
        """
        if 'lang' in self.request.GET:
            lang = self.request.GET['lang'].lower()
            if lang in settings.LANGUAGE_URL_MAP:
                return settings.LANGUAGE_URL_MAP[lang]

        if self.request.META.get('HTTP_ACCEPT_LANGUAGE'):
            best = get_best_language(
                self.request.META['HTTP_ACCEPT_LANGUAGE'])
            if best:
                return best

        return settings.LANGUAGE_CODE

    def get_chosen_language(self):
        """If the request has a cookie set for language, return that language."""
        language = self.request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

        # Need to check if his cookie language is supported by Kuma.
        if language and language in dict(settings.LANGUAGES):
            return language

    def fix(self, path):
        path = path.lstrip('/')
        url_parts = [self.request.META['SCRIPT_NAME']]
        if path.endswith('/'):
            check_path = path
        else:
            check_path = path + '/'
        if not check_path.startswith(settings.LANGUAGE_URL_IGNORED_PATHS):
            # Set locale according to order
            locale = self.locale or self.get_language()
            url_parts.append(locale)

        url_parts.append(path)

        return '/'.join(url_parts)
