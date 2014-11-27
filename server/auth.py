import datetime
import jwt


class TokenAuthentication(object):
  def __init__(self, jwt_secret, provide_request, token_ttl):
    self.secret = jwt_secret
    self.ttl = token_ttl
    self.provide_request = provide_request

  def generate_token(self, user_id):
    claim = dict(user_id=user_id, exp=datetime.datetime.utcnow() + self.ttl)
    return jwt.encode(claim, self.secret)

  def get_claim(self, request):
    token = request.headers.get('JWT')
    if token is None:
      return None
    try:
      return jwt.decode(token, self.secret)
    except:
      return None

  def get_user_id(self):
    claim = self.get_claim(self.provide_request())
    if claim is None:
      return None
    user_id = claim.get('user_id')
    if not isinstance(user_id, int):
      return None
    else:
      return user_id
