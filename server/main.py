import wiring
import rest_server


if __name__ == '__main__':
  injector = wiring.web_graph(wiring.CmdlineModule(), wiring.DevConfigModule())
  web_server = injector.provide(rest_server.WebServer)
  web_server.run()
else:
  app = wiring.web_graph().provide(rest_server.App).wsgi
