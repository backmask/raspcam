import shelve

def config_get(key):
  d = shelve.open(CONFIG_FILE)
  if not d.has_key(key):
    return False
  v = d[key]
  d.close()
  return v

def config_set(key, value):
  d = shelve.open(CONFIG_FILE)
  d[key] = value
  d.close()

def config_set_default(key, defaultValue):
  d = shelve.open(CONFIG_FILE)
  if not d.has_key(key):
    d[key] = defaultValue
  d.close()

CONFIG_FILE = "config.db"
DEFAULT_CONFIG = {
  # Global parameters
  "listen_host": "0.0.0.0",
  "listen_port": 8082,
  "auth_login": "admin",
  "auth_password": "admin",

  # PTZ parameters
  "pan_servo": 6,
  "tilt_servo": 5,
  "pan_center": "50%",
  "tilt_center": "50%",
  "pan_step": "5%",
  "tilt_step": "5%",

  # Raspberry parameters
  "raspberry_horizontal_flip": True,
  "raspberry_vertical_flip": True,
  "raspberry_resolution_x": 1920,
  "raspberry_resolution_y": 1024,
  "raspberry_base_quality": 80,

  # Timelapse
  "timelapse_folder": "timelapse",
  "timelapse_max_storage_volume": 5000,
  "timelapse_max_storage_time": 60 * 24,
  "timelapse_frame_interval": 10,
  "timelapse_framerate": 60,
  "timelapse_resolution": "852x480",
  "timelapse_encoder": "omxtx",
}

# Set default values
for key in DEFAULT_CONFIG.keys():
  config_set_default(key, DEFAULT_CONFIG[key])

# Executor
from executor_raspberry import ExecutorRaspberry
executor = ExecutorRaspberry(
  panServoId=config_get("pan_servo"),
  tiltServoId=config_get("tilt_servo"))

# Scheduler
from apscheduler.scheduler import Scheduler
from apscheduler.jobstores.shelve_store import ShelveJobStore
import atexit
sched = Scheduler(daemon=True)
sched.add_jobstore(ShelveJobStore('sched.db'), 'file')
atexit.register(lambda: sched.shutdown(wait=False))
sched.start()

# Logging
import logging
import sys

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

root = logging.getLogger()
root.addHandler(ch)