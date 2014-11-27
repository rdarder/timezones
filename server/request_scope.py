import threading
from pinject import Scope, BindingSpec, provides
import pinject


class RequestScope(Scope):
  def __init__(self, request_scope_middleware):
    self.middleware = request_scope_middleware

  def provide(self, binding_key, default_provider_fn):
    if binding_key not in self.middleware:
      self.middleware[binding_key] = to_provide = default_provider_fn()
      return to_provide
    else:
      return self.middleware[binding_key]

  @classmethod
  def external_dep(cls):
    raise RuntimeError('Cannot resolve dependency through a provider')


class RequestScopeMiddleware(object):
  def __init__(self):
    self.local = threading.local()

  def __contains__(self, item):
    return item in self.local.store

  def __getitem__(self, item):
    return self.local.store[item]

  def __setitem__(self, key, item):
    self.local.store[key] = item

  def __call__(self, request, response, app):
    self.local.store = dict()
    self.local.request = request
    response = app(request, response)
    del self.local.store
    del self.local.request
    return response


class RequestScopeModule(BindingSpec):
  def __init__(self):
    self.middleware = RequestScopeMiddleware()
    self.scope = RequestScope(self.middleware)
    self.id_to_scope = dict(request=self.scope)

  @provides(in_scope='request')
  def provide_request(self):
    return self.middleware.local.request

  def is_usable(self, inner, outer):
    return True
    #return not (inner == 'request' and outer == pinject.SINGLETON)






