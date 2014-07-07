import requests

class ExecutorMotion:
  host = False
  streamPort = False
  controlPort = False
  thread = 0

  def __init__(self, host, streamPort=8081, controlPort=8080, thread=0):
    self.host = host
    self.thread = thread
    self.streamPort = streamPort
    self.controlPort = controlPort

  def build_url(self, fragment, stream=False):
    return self.host + ":" + (str(self.streamPort) if stream else str(self.controlPort)) \
      + ("" if stream else "/" + str(self.thread)) \
      + fragment

  def video_stream(self):
    r = requests.get(self.build_url("/", stream=True), stream=True)
    for chunk in r.iter_content(chunk_size=8192):
      if chunk:
        yield chunk

  def stop(self):
    pass

  def center(self):
    requests.get(self.build_url("/track/center"))

  def up(self):
    requests.get(self.build_url("/track/set"), params={"pan":0, "tilt": -5});

  def down(self):
    requests.get(self.build_url("/track/set"), params={"pan":0, "tilt": -5});

  def left(self):
    requests.get(self.build_url("/track/set"), params={"pan":5, "tilt": 0});

  def right(self):
    requests.get(self.build_url("/track/set"), params={"pan":-5, "tilt": 0});

  def vertical_patrol(self):
    pass

  def horizontal_patrol(self):
    pass