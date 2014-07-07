import picamera
import io
import time
from config import config_get
from threading import Lock, Condition, Thread

class CameraWorker:

  def __init__(self):
    self.frame_cd = Condition()
    self.frame = False
    self.keep_working = True
    self.worker = Thread(target=self.work)
    self.worker.start()

  def work(self):
    camera = picamera.PiCamera()
    camera.hflip = config_get("raspberry_horizontal_flip")
    camera.vflip = config_get("raspberry_vertical_flip")
    camera.resolution = (
      config_get("raspberry_resolution_x"),
      config_get("raspberry_resolution_y")
    )
    camera.start_preview()
    time.sleep(2)
    stream = io.BytesIO()
    released = True

    try:
      for notUsed in camera.capture_continuous(stream, format='jpeg', resize=None, quality=config_get("raspberry_base_quality")):
        self.frame_cd.acquire()
        released = False
        self.frame = stream.getvalue()
        self.frame_cd.notify_all()
        self.frame_cd.release()
        released = True
        stream.seek(0)
        stream.truncate()
        if not self.keep_working:
          break
    finally:
      camera.close()
      if not released: self.frame_cd.release()

  def close(self):
    self.keep_working = False
    self.worker.join()

  def get_picture(self):
    self.frame_cd.acquire()
    self.frame_cd.wait(5)
    frame_cpy = self.frame
    self.frame_cd.release()
    return frame_cpy

  def stream(self):
    try:
      self.frame_cd.acquire()
      while self.keep_working:
        self.frame_cd.wait(5)
        yield self.frame
    finally:
      self.frame_cd.release()

class LazySingleton:

  def __init__(self, builder, destroyer = False):
    self.instance = False
    self.references = 0
    self.builder = builder
    self.destroyer = destroyer
    self.mutex = Lock()

  def get(self):
    self.references += 1
    if not self.instance:
      self.mutex.acquire()
      try:
        if not self.instance:
          self.instance = self.builder()
      finally:
        self.mutex.release()
    return self.instance

  def release(self):
    self.references -= 1
    if self.references <= 0:
      self.mutex.acquire()
      try:
        if self.references <= 0:
          if self.destroyer: self.destroyer(self.instance)
          self.instance = False
      finally:
        self.mutex.release()

class ExecutorRaspberry:

  def __init__(self, panServoId=False, tiltServoId=False):
    self.panServoId = panServoId
    self.tiltServoId = tiltServoId
    self.camera = LazySingleton(
      builder = lambda: CameraWorker(),
      destroyer = lambda w: w.close()
    )

  def video_stream(self):
    cam = self.camera.get()
    try:
      for frame in cam.stream():
        yield "Content-Type: image/jpeg\r\n"
        yield "Content-length: "+ str(len(frame)) + "\r\n\r\n"
        yield frame
        yield "\r\n\r\n\r\n"
        yield "--BoundaryString\r\n"
    finally:
      self.camera.release()

  def snapshot(self):
    cam = self.camera.get()
    try:
      return cam.get_picture()
    finally:
      self.camera.release()

  def stop(self):
    pass

  def center(self):
    self.servo_write(self.panServoId, config_get("pan_center"))
    self.servo_write(self.tiltServoId, config_get("tilt_center"))

  def up(self):
    self.servo_write(self.tiltServoId, "-" + config_get("tilt_step"))

  def down(self):
    self.servo_write(self.tiltServoId, "+" + config_get("tilt_step"))

  def left(self):
    self.servo_write(self.panServoId, "+" + config_get("pan_step"))

  def right(self):
    self.servo_write(self.panServoId, "-" + config_get("pan_step"))

  def vertical_patrol(self):
    pass

  def horizontal_patrol(self):
    pass

  def servo_write(self, servoId, value):
    if not servoId or not value: return

    f = open('/dev/servoblaster', 'w')
    if f:
      f.write('%d=%s\n' % (servoId, value))
      f.close()