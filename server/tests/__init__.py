import json
import threading
import unittest
import requests
import rest_server
import yaml


class TimezonesClient(object):
  def __init__(self, host, port, base_path=''):
    self.host = host
    self.port = port
    self.base_path = base_path
    port_spec = '' if port == 80 else ':{}'.format(port)
    self.base_url = "http://{}{}{}".format(host, port_spec, base_path)
    self.headers = {'content-type': 'application/json'}

  def request(self, url, method, payload=None):
    data = None if payload is None else json.dumps(payload)
    return requests.request(method, '/'.join([self.base_url, url]),
                            data=data, headers=self.headers)

  def set_token(self, token):
    self.headers['JWT'] = token

  def clear_token(self):
    if 'JWT' in self.headers:
      del self.headers['JWT']

  def create(self, resource, value):
    return self.request(resource, 'POST', value)

  def list(self, resource):
    return self.request(resource, 'GET')

  def get(self, resource, id):
    return self.request(self._resource_id(resource, id), 'GET')

  def delete(self, resource, id):
    return self.request(self._resource_id(resource, id), 'DELETE')

  def _resource_id(self, resource, id):
    return '/'.join((resource, str(id)))

  def update(self, resource, id, value):
    return self.request(self._resource_id(resource, id), 'PUT', value)

  def login(self, user, password):
    r = self.create('auth', dict(login=user, password=password))
    if r.status_code == requests.codes.ok:
      self.set_token(r.json()['token'])
      return True
    else:
      return False

  def logout(self):
    self.clear_token()


class Base(unittest.TestCase):
  def basic_user(self):
    self.assertOk(client.create('users', dict(login='test1', password='test1')))
    self.assertTrue(client.login('test1', 'test1'))

  def setUp(self):
    server.remote_restart()

  def tearDown(self):
    client.logout()

  def assert_code(self, response, code):
    if response.status_code != code:
      try:
        body = yaml.safe_dump(response.json(), default_flow_style=False)
      except:
        body = ''
      self.fail(msg="expected {}, got {}.\n\n{}"
                .format(code, response.status_code, body))

  def assertValidationError(self, response):
    self.assertBadRequest(response)
    self.assertEquals('Validation Error', response.json()['description'])

  def assertOk(self, response):
    return self.assert_code(response, 200)

  def assertBadRequest(self, response):
    return self.assert_code(response, 400)

  def assertUnauthorized(self, response):
    return self.assert_code(response, 401)

  def assertForbidden(self, response):
    return self.assert_code(response, 403)

  def assertNotFound(self, response):
    return self.assert_code(response, 404)


server = client = None


def setup():
  global server, client
  port = 8001
  host = 'localhost'
  restart_path = '/restart'
  stop_path = '/stop'
  server = rest_server.RemoteRestartableApp(host, port, restart_path)
  threading.Thread(target=server.run).start()
  client = TimezonesClient(host, port)


def teardown():
  server.shutdown()


class TestRegistrationAndLogin(Base):
  def testLoginRegister(self):
    self.assertFalse(client.login('test1', 'test1'))
    response = client.create('users', dict(login='test1', password='test1'))
    self.assertOk(response)
    self.assertFalse(client.login('test1', 'test2'))
    self.assertTrue(client.login('test1', 'test1'))

  def testLoginTwice(self):
    self.basic_user()
    self.assertTrue(client.login('test1', 'test1'))


  def testRepeatedUserLogin(self):
    self.assertOk(client.create('users', dict(login='test1', password='test1')))
    repeated = client.create('users', dict(login='test1', password='test1'))
    self.assertBadRequest(repeated)
    self.assertEquals('Validation Error', repeated.json()['description'])


  def testMissingRegisterField(self):
    reg = client.create('users', dict(password='test1'))
    self.assertValidationError(reg)


  def testNameIsOptional(self):
    reg = client.create('users', dict(login='test1', password='test1'))
    self.assertOk(reg)


class TestTimezonesCrud(Base):
  def testNoTimezones(self):
    self.basic_user()
    response = client.list('timezones')
    self.assertOk(response)
    self.assertEquals([], response.json())

  def testOneTimezone(self):
    self.basic_user()
    self.assertOk(client.create(
      'timezones',
      dict(city='Rosario', name="ART", gmt_delta_seconds=-1440)
    ))

    timezones = client.list('timezones').json()
    self.assertEquals(1, len(timezones))
    self.assertEquals('Rosario', timezones[0]['city'])


  def testDeleteExisting(self):
    self.basic_user()
    t = client.create('timezones',
                      dict(city='Rosario', name="ART", gmt_delta_seconds=-1440))
    timezone_id = t.json()['id']
    r = client.delete('timezones', timezone_id)
    self.assertOk(r)

  def testDeleteTwiceSucceedOnce(self):
    self.basic_user()
    t = client.create('timezones',
                      dict(city='Rosario', name="ART", gmt_delta_seconds=-1440))
    timezone_id = t.json()['id']
    r = client.delete('timezones', timezone_id)
    self.assertOk(r)
    r2 = client.delete('timezones', timezone_id)
    self.assertNotFound(r2)

  def testUpdateSimple(self):
    self.basic_user()
    base = dict(city='Rosario', name="ART", gmt_delta_seconds=-1440)
    t = client.create('timezones', base)
    id = t.json()['id']
    base.update(city='New York')
    u = client.update('timezones', id, base)
    self.assertOk(u)
    self.assertEquals('New York', u.json()['city'])
    l = client.get('timezones', id)
    self.assertOk(l)
    self.assertEquals('New York', l.json()['city'])


class TestTimezoneOwnership(Base):
  def _user2(self):
    self.assertOk(client.create('users', dict(login='test2', password='pass2')))
    self.assertTrue(client.login('test2', 'pass2'))

  def testDontShareTimezones(self):
    self.assertOk(client.create('users', dict(login='test1', password='pass1')))
    self.assertOk(client.create('users', dict(login='test2', password='pass2')))
    client.login('test1', 'pass1')
    c = client.create('timezones', dict(city='Rosario', name="ART",
                                        gmt_delta_seconds=-1440))
    id1 = c.json()['id']
    client.logout()
    client.login('test2', 'pass2')
    self.assertNotFound(client.get('timezones', id1))
    self.assertNotFound(client.update('timezones', id1, dict()))
    self.assertNotFound(client.delete('timezones', id1))
    c = client.create('timezones', dict(city='Cordoba', gmt_delta_seconds=-820))
    id2 = c.json()['id']
    self.assertOk(client.get('timezones', id2))
    client.logout()
    client.login('test1', 'pass1')
    self.assertNotFound(client.get('timezones', id2))
    self.assertNotFound(client.update('timezones', id2, dict()))
    self.assertNotFound(client.delete('timezones', id2))
