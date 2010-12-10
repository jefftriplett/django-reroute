from functools import partial

from django.conf.urls.defaults import patterns as django_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver

from utils import rollup

class RerouteRegexURLPattern(RegexURLPattern):
    _configured = False
    
    def reroute_config(self, wrappers, patterns_id):
        self.wrappers = wrappers
        self._configured = True
        
    def reroute_callback(self, request, *args, **kwargs):
        callback = rollup(self.callback, self.wrappers)
        return callback(request, *args, **kwargs)
                  
    def resolve(self, path):
        # Lifted from django.core.urlresolvers.RegexURLPattern.resolve
        if not self._configured:
            raise ImproperlyConfigured('RerouteRegexURLPattern patterns must be used within reroute.patterns or reroute_patterns (for pattern %r)' % self.regex.pattern)
        
        match = self.regex.search(path)
        if match:
            # If there are any named groups, use those as kwargs, ignoring
            # non-named groups. Otherwise, pass all non-named arguments as
            # positional arguments.
            kwargs = match.groupdict()
            if kwargs:
                args = ()
            else:
                args = match.groups()
            # In both cases, pass any extra_kwargs as **kwargs.
            kwargs.update(self.default_args)
        
            return self.reroute_callback, args, kwargs

def reroute_patterns(wrappers, prefix, *args):
    # TODO(dnerdy) Require that all patterns be instances of RerouteRegexURLPattern
    # TODO(dnerdy) Remove additional patterns with identical regexes, if present (occurs
    #   when using verb_url)
    
    patterns_id = object()
    pattern_list = django_patterns(prefix, *args)
    
    for pattern in pattern_list:
        if isinstance(pattern, RerouteRegexURLPattern):            
            pattern.reroute_config(wrappers, patterns_id)
        
    return pattern_list
    
patterns = partial(reroute_patterns, [])

def url_with_pattern_class(pattern_class, regex, view, kwargs=None, name=None, prefix=''):
    # Lifted from django.conf.urls.defaults
    
    if isinstance(view, (list,tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return RegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    else:
        if isinstance(view, basestring):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return pattern_class(regex, view, kwargs, name)
        
url = partial(url_with_pattern_class, RerouteRegexURLPattern)