from models import User, Timezone
import re


class UserDto(object):
  alpha_re = re.compile('^[a-zA-Z][0-9a-zA-Z]+$')

  def __init__(self, password_manager):
    self.password_manager = password_manager

  def to_msg(self, user):
    return dict(login=user.login, name=user.name)

  def from_msg(self, msg):
    user = User()
    self.populate(user, msg)
    return user


  def validate_login(self, msg):
    errors = []
    if not isinstance(msg, dict):
      return [("", "type error")]
    login = msg.get('login')
    if login is None:
      errors.append(('login', 'is missing'))
    elif not isinstance(login, basestring):
      errors.append(('login', 'must be a string'))
    elif len(login) > 50:
      errors.append(('login', 'must be shorter than 50 characters'))
    elif len(login) < 5:
      errors.append(("login", 'must be at least 5 characters long'))
    if not self.alpha_re.match(login):
      errors.append(("login", "must begin followed by alphanumerics"))
    password = msg.get('password')
    if password is None:
      errors.append(('password', 'is missing'))
    elif not isinstance(password, basestring):
      errors.append(('password', 'must be a string'))
    elif len(password) < 5:
      errors.append(("password", 'must be at least 5 characters long'))
    return errors

  def validate(self, msg):
    errors = []
    if not isinstance(msg, dict):
      return [("", "type error")]
    login = msg.get('login')
    if login is None:
      errors.append(('login', 'is missing'))
    elif not isinstance(login, basestring):
      errors.append(('login', 'must be a string'))
    elif len(login) > 50:
      errors.append(('login', 'must be shorter than 50 characters'))
    elif len(login) < 5:
      errors.append(("login", 'must be at least 5 characters long'))
    elif not self.alpha_re.match(login):
      errors.append(("login", "must begin followed by alphanumerics"))

    password = msg.get('password')
    if password is None:
      errors.append(('password', 'is missing'))
    elif not isinstance(password, basestring):
      errors.append(('password', 'must be a string'))
    elif len(password) < 5:
      errors.append(("password", 'must be at least 5 characters long'))

    name = msg.get('name')
    if name is None:
      pass
    elif not isinstance(name, basestring):
      errors.append(('name', 'must be a string'))
    elif len(name) < 5:
      errors.append(("name", 'must be at least 5 characters long'))
    elif len(name) > 50:
      errors.append(("name", 'must be shorter than 50 characters'))

    return errors

  def validate_ref_args(self, args):
    errors = []
    if not isinstance(args, dict):
      errors.append(('', 'type error'))
    elif 'id' not in args:
      errors.append(('id', 'is missing'))
    elif not isinstance(args['id'], int):
      errors.append(('id', 'type error'))
    return errors

  def populate(self, user, msg):
    user.login = msg['login']
    user.name = msg.get('name')
    user.password = self.password_manager.encrypt(msg['password'])


class TimezoneDto(object):
  def to_msg(self, timezone):
    return dict(
      id=timezone.id,
      gmt_delta_seconds=timezone.gmt_delta_seconds,
      city=timezone.city
    )

  def validate(self, msg):
    errors = []
    if not isinstance(msg, dict):
      return [('', 'type error')]
    gmt_delta_seconds = msg.get('gmt_delta_seconds')
    if gmt_delta_seconds is None:
      errors.append(('gmt_delta_seconds', 'is missing'))
    elif not isinstance(gmt_delta_seconds, int):
      errors.append(('gmt_dela_seconds', 'must be an integer'))
    elif not -15 * 60 * 60 < gmt_delta_seconds < 15 * 60 * 60:
      errors.append(('gmt_delta_seconds', 'value out of range'))

    city = msg.get('city')
    if city is None:
      errors.append(('city', 'is missing'))
    elif not isinstance(city, basestring):
      errors.append(('city', 'must be a string'))
    elif len(city) == 0:
      errors.append(('city', 'must not be empty'))
    elif len(city) > 200:
      errors.append(('city', 'must be shorter than 200 characters'))
    return errors

  def validate_ref_args(self, args):
    errors = []
    if not isinstance(args, dict):
      errors.append(('', 'type error'))
    elif 'id' not in args:
      errors.append(('id', 'is missing'))
    elif not isinstance(args['id'], int):
      errors.append(('id', 'type error'))
    return errors


  def from_msg(self, msg):
    timezone = Timezone()
    self.populate(timezone, msg)
    return timezone

  def populate(self, timezone, msg):
    timezone.gmt_delta_seconds = msg["gmt_delta_seconds"]
    timezone.city = msg['city']
