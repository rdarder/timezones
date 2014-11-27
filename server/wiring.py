import argparse
import base64
import json
import datetime
import passlib.hash
import pinject
import auth
import request_scope
import rest_server

#keep these unused imports, pinject needs them to find providers
import services, dto, db


class WebModule(pinject.BindingSpec):
  def __init__(self, req_scope_middleware):
    self.req_scope_middleware = req_scope_middleware

  def configure(self, bind):
    bind('auth', to_class=auth.TokenAuthentication)
    bind('json_encoder', to_class=json.JSONEncoder)
    bind('token_ttl', to_instance=datetime.timedelta(hours=24))
    bind('password_manager', to_instance=passlib.hash.sha256_crypt)
    bind('request_cls', to_instance=rest_server.JSONRequest)

  def provide_web_app(self, json_exception_wrapper, rest_router, user_service,
                      timezone_service, auth_service):
    rest_router.add_rule(rest_server.RestRules('/auth').create,
                         auth_service.login)
    rest_router.add_resource(user_service, '/users')
    rest_router.add_resource(timezone_service, '/timezones')
    return rest_server.MiddlewareLink.build(
      [json_exception_wrapper, self.req_scope_middleware], rest_router)


class CmdlineModule(pinject.BindingSpec):
  def provide_cmdline_args(self):
    parser = argparse.ArgumentParser(description='Timezone server.')
    parser.add_argument('--host', default='0.0.0.0', help='bind address')
    parser.add_argument('--port', type=int, default=8000, help='bind port')
    parser.add_argument('--client', type=str, default='../client',
                        help='serve web app static files')
    return parser.parse_args()

  def provide_host(self, cmdline_args):
    return cmdline_args.host

  def provide_port(self, cmdline_args):
    return cmdline_args.port

  def provide_client_folder(self, cmdline_args):
    return cmdline_args.client


class DevConfigModule(pinject.BindingSpec):
  def configure(self, bind):
    bind('db_url', to_instance='sqlite:///db/db.sqlite')
    bind('db_verbose', to_instance=True)

  def provide_jwt_secret(self):
    return base64.decodestring(open('jwt_secret.txt').read())


class TestConfigModule(pinject.BindingSpec):
  def configure(self, bind):
    bind('db_url', to_instance='sqlite://')  #in memory
    bind('db_verbose', to_instance=False)

  def provide_jwt_secret(self):
    return 'test'


def web_graph(*extra_specs):
  req_scope_module = request_scope.RequestScopeModule()
  specs = [req_scope_module,
           WebModule(req_scope_module.middleware),
           db.DbModule()] + list(extra_specs)
  return pinject.new_object_graph(
    binding_specs=specs,
    id_to_scope=req_scope_module.id_to_scope,
    is_scope_usable_from_scope=req_scope_module.is_usable
  )


