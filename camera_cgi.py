from flask import Flask, request, abort, make_response, render_template, redirect, url_for
from auth import *
from config import *
from timelapse import *

app = Flask(__name__)
app.register_blueprint(timelapse_cgi)

@app.route("/")
@requires_auth
def home():
  return render_template("index.html")

@app.route("/videostream.cgi")
@requires_auth
def stream():
  return Response(executor.video_stream(), mimetype="multipart/x-mixed-replace;boundary=--BoundaryString")

@app.route("/snapshot.cgi")
@requires_auth
def snapshot():
  return Response(executor.snapshot(), mimetype="image/jpeg")

@app.route("/decoder_control.cgi")
@requires_auth
def control():
  if "command" not in request.args:
    abort(make_response("Invalid grammar, expected command querystring parameter", 400))

  cmd = int(request.args.get("command"))
  if cmd == 0: # up
    executor.up()
  elif cmd == 2: # down
    executor.down()
  elif cmd == 4: # left
    executor.left()
  elif cmd == 6: # right
    executor.right()
  elif cmd == 25: # center
    executor.center()
  elif cmd == 26: # vertical patrol
    executor.vertical_patrol()
  elif cmd == 29: # horizontal patrol
    executor.horizontal_patrol()
  elif cmd in [1, 3, 5, 7, 27, 30]:
    executor.stop()
  else:
      abort(make_response("Unknown command", 400))

  return "Ok!"

@app.route("/config/set/<key>/<value>")
@requires_auth
def set_config(key, value):
  config_set(str(key), str(value))
  return "Ok!"

@app.route("/config")
@requires_auth
def config():
  d = shelve.open(CONFIG_FILE)
  exp = []
  for k, v in d.iteritems():
    if type(v) is int:
      exp.append((k, v, 'number'))
    elif type(v) is bool:
      exp.append((k, v, 'boolean'))
    else:
      exp.append((k, v, 'string'))
  d.close()
  tmpl = render_template("config.html",
    config = sorted(exp, key=lambda v: v[0]))
  return tmpl

@app.route("/config/set", methods=['POST'])
@requires_auth
def set_config_all():
  d = shelve.open(CONFIG_FILE)
  for key in request.form.keys():
    val = request.form[key]
    if d.has_key(key):
      cval = d[key]
      if type(cval) is int:
        val = int(val)
      elif type(cval) is bool:
        val = True if val != '0' else False
    d[key] = val
  d.close()
  return redirect(url_for('config'))

if __name__ == "__main__":
  app.run(
    host=config_get("listen_host"),
    port=config_get("listen_port"),
    debug=True,
    threaded=True,
    use_reloader=False)