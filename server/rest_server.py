import json
import threading
import wsgiref.simple_server
import pinject
import requests
from werkzeug.exceptions import HTTPException
from werkzeug.http import parse_options_header
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
from wsgiref import simple_server
from db import DbCreator
import wiring


class JSONRequest(Request):
  # accept up to 4MB of transmitted data.
  max_content_length = 1024 * 1024 * 4

  @cached_property
  def msg(self):
    content_type, _ = parse_options_header(self.headers.get('content-type'))
    if (content_type == 'application/json' and len(self.data) > 0):
      return json.loads(self.data)


class RestRouter(object):
  def __init__(self, json_encoder):
    self.handlers = {}
    self.map = Map()
    self.encoder = json_encoder

  def add_rule(self, rule, fn):
    if rule.endpoint in self.handlers:
      raise ValueError("Endpoint {} already present".format(rule.endpoint))
    self.handlers[rule.endpoint] = fn
    self.map.add(rule)

  def add_resource(self, service, path):
    rules = RestRules(path)
    for method in RestRules.METHOD_NAMES:
      if callable(getattr(service, method, None)):
        self.add_rule(getattr(rules, method), getattr(service, method))

  def __call__(self, request, response):
    matcher = self.map.bind_to_environ(request.environ)
    endpoint, args = matcher.match()
    handler = self.handlers[endpoint]
    result = handler(args, request)
    if isinstance(result, Response):
      return result
    elif result is not None:
      response.set_data(self.encoder.encode(result))
      response.content_type = 'application/json'
      return response
    else:
      return response


class RestRules(object):
  METHOD_NAMES = frozenset({'get', 'list', 'update', 'create', 'delete'})

  def __init__(self, path):
    self.get = Rule(path + '/<int:id>', methods=['GET'], endpoint=path + '/get')
    self.update = Rule(path + '/<int:id>', methods=['PUT'],
                       endpoint=path + '/update')
    self.delete = Rule(path + '/<int:id>', methods=['DELETE'],
                       endpoint=path + '/delete')
    self.list = Rule(path, methods=['GET'], endpoint=path + '/list')
    self.create = Rule(path, methods=['POST'], endpoint=path + '/create')


class MiddlewareLink(object):
  def __init__(self, middleware, app):
    self.middleware = middleware
    self.app = app

  def __call__(self, request, response):
    return self.middleware(request, response, self.app)

  @classmethod
  def build(cls, middleware_list, app):
    for middleware in reversed(middleware_list):
      app = MiddlewareLink(middleware, app)
    return app


class WsgiWrapper(object):
  @pinject.inject(['request_cls'])
  def __init__(self, handler, request_cls):
    self.handler = handler
    self.request_cls = request_cls

  def __call__(self, environ, start_response):
    response = self.handler(self.request_cls(environ), Response())
    return response(environ, start_response)


class JsonExceptionWrapper(object):
  def __init__(self, json_encoder):
    self.json_encoder = json_encoder

  def __call__(self, request, response, app):
    try:
      return app(request, response)
    except HTTPException, e:
      return Response(
        response=self.json_encoder.encode(
          dict(description=e.description, code=e.code)),
        content_type='application/json',
        status=e.code
      )


class WebServer(object):
  def __init__(self, host, port, app, client_folder):
    if client_folder == '':
      web_app = app.wsgi
    else:
      web_app = SharedDataMiddleware(app.wsgi, {'/client': client_folder})
    self.server = wsgiref.simple_server.make_server(host, port, web_app)

  def run(self):
    self.server.serve_forever()


class App(object):
  def __init__(self, provide_wsgi_wrapper, web_app):
    self.wsgi = provide_wsgi_wrapper(web_app)


class RemoteRestartableApp(object):
  def __init__(self, host, port, restart_path):
    self.restart_path = restart_path
    self.server = simple_server.make_server(host, port, self)
    self.app = None
    self.setup_app()
    self.base_url = "http://{}{}".format(
      host,
      '' if port == 80 else ':{}'.format(port)
    )

  def run(self):
    self.server.serve_forever()

  def setup_app(self):
    injector = wiring.web_graph(wiring.TestConfigModule())
    db_creator = injector.provide(DbCreator)
    db_creator.create_db()
    self.app = injector.provide(App).wsgi

  def is_restart_request(self, environ):
    return (environ['REQUEST_METHOD'] == 'POST' and
            environ['PATH_INFO'] == self.restart_path)

  def remote_restart(self):
    requests.request('POST', self.base_url + self.restart_path)

  def shutdown(self):
    self.server.shutdown()

  def __call__(self, environ, start_response):
    if self.is_restart_request(environ):
      self.setup_app()
      start_response("200 OK", [('content-type', 'text/plain')], None)
      return []
    else:
      return self.app(environ, start_response)
