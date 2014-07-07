from functools import wraps
from flask import request, Response
from config import config_get

def check_auth(username, password):
  return username == config_get("auth_login") and password == config_get("auth_password")

def authenticate():
  return Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    auth = request.authorization
    isHttpAuth = auth and check_auth(auth.username, auth.password)
    isQSAuth = "user" in request.args and "pwd" in request.args and check_auth(request.args.get("user"), request.args.get("pwd"))

    if not isHttpAuth and not isQSAuth:
      return authenticate()

    return f(*args, **kwargs)
  return decorated
