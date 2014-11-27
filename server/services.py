from itertools import groupby
import json
from models import User, Timezone
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers import Response


class Errors(object):
  def error(description, code):
    response = Response()
    response.data = json.dumps(dict(description=description))
    response.status_code = code
    return response

  @staticmethod
  def validation(errors, code=400):
    response = Response()
    response.status_code = code
    grouped = {field: tuple(e[1] for e in errors)
               for field, errors in groupby(sorted(errors), lambda e: e[0])}
    body = dict(description="Validation Error", details=dict(fields=grouped))
    response.data = json.dumps(body)
    return response

  Unauthorized = error("Invalid credentials", 401)
  Forbidden = error("Access denied", 403)
  NotFound = error("Not found", 404)
  error = staticmethod(error)


class AuthMixin(object):
  def __init__(self, auth, session_context):
    self.auth = auth
    self.session_context = session_context

  def _get_user(self):
    user_id = self.auth.get_user_id()
    if user_id is None:
      return None
    else:
      return self.session_context.session.query(User).get(user_id)


class UserService(AuthMixin):
  def __init__(self, user_dto, auth, session_context):
    super(UserService, self).__init__(auth, session_context)
    self.user_dto = user_dto


  def create(self, args, request):
    errors = self.user_dto.validate(request.msg)
    if len(errors) > 0:
      return Errors.validation(errors)
    user = self.user_dto.from_msg(request.msg)
    session = self.session_context.session
    try:
      session.add(user)
      session.commit()
      return self.user_dto.to_msg(user)
    except IntegrityError, e:
      session.rollback()
      return Errors.validation([('login', 'is already taken')])


  def delete(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    else:
      with self.session_context() as session:
        session.delete(user)

  def get(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    else:
      return self.user_dto.to_msg(user)

  def update(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    else:
      errors = self.user_dto.validate(request.msg)
      if len(errors) > 0:
        return Errors.validation(errors)
      self.user_dto.populate(user, request.msg)
      with self.session_context() as session:
        session.add(user)
      return self.user_dto.to_msg(user)


class AuthService(object):
  def __init__(self, password_manager, auth, session_context, user_dto):
    self.password_manager = password_manager
    self.auth = auth
    self.session_context = session_context
    self.user_dto = user_dto

  def login(self, args, request):
    msg = request.msg
    errors = self.user_dto.validate_login(msg)
    if len(errors) > 0:
      return Errors.validation(errors)
    with self.session_context() as session:
      user = session.query(User).filter(User.login == msg['login']).first()
      if user is not None and self.password_manager.verify(msg['password'],
                                                           user.password):
        return dict(token=self.auth.generate_token(user.id))
      else:
        return Errors.Unauthorized


class TimezoneService(AuthMixin):
  def __init__(self, timezone_dto, auth, session_context):
    super(TimezoneService, self).__init__(auth, session_context)
    self.timezone_dto = timezone_dto

  @staticmethod
  def _user_timezones(session, user_id):
    return session.query(Timezone).filter(Timezone.user_id == user_id)

  def create(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    errors = self.timezone_dto.validate(request.msg)
    if len(errors) > 0:
      return Errors.validation(errors)
    with self.session_context() as session:
      timezone = self.timezone_dto.from_msg(request.msg)
      timezone.user_id = user.id
      session.add(timezone)
    return self.timezone_dto.to_msg(timezone)

  def update(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    errors = self.timezone_dto.validate_ref_args(args)
    if len(errors) > 0:
      return Errors.validation(errors)
    with self.session_context() as session:
      timezone = self._user_timezones(session, user.id).filter(
        Timezone.id == args['id']).first()
      if timezone is None:
        return Errors.NotFound
      errors = self.timezone_dto.validate(request.msg)
      if len(errors) > 0:
        return Errors.validation(errors)
      self.timezone_dto.populate(timezone, request.msg)
      session.add(timezone)
    return self.timezone_dto.to_msg(timezone)

  def get(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    errors = self.timezone_dto.validate_ref_args(args)
    if len(errors) > 0:
      return Errors.validation(errors)
    with self.session_context() as session:
      timezone = self._user_timezones(session, user.id).filter(
        Timezone.id == args['id']).first()
      if timezone is None:
        return Errors.NotFound
      return self.timezone_dto.to_msg(timezone)

  def list(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    with self.session_context() as session:
      timezones = self._user_timezones(session, user.id)
      query = request.args.get('q')
      if query is not None and isinstance(query, basestring) and len(query) > 0:
        timezones = timezones.filter(
          Timezone.city.contains(query))
      return [self.timezone_dto.to_msg(t) for t in timezones]

  def delete(self, args, request):
    user = self._get_user()
    if user is None:
      return Errors.Unauthorized
    errors = self.timezone_dto.validate_ref_args(args)
    if len(errors) > 0:
      return Errors.validation(errors)
    with self.session_context() as session:
      found = self._user_timezones(session, user.id).filter(
        Timezone.id == args['id']).delete()
      if found == 0:
        return Errors.NotFound
