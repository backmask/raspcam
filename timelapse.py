import Queue
import time
import os
import io
from datetime import date, timedelta, datetime
from config import *

def take_timelapse_picture():
  timestamp = datetime.fromtimestamp(time.time())
  folder = os.path.join(
    config_get("timelapse_folder"),
    "raw",
    timestamp.strftime('%Y-%m-%d'))
  fileName = timestamp.strftime('%H%M%S') + ".jpg"

  if not os.path.exists(folder):
    os.makedirs(folder)

  from PIL import Image, ImageDraw
  timestampXY = (40, int(config_get("timelapse_resolution").split('x')[1]) - 40)

  snapshot = executor.snapshot()
  if snapshot:
    img = Image.open(io.BytesIO(snapshot))
    draw = ImageDraw.Draw(img)
    draw.text(timestampXY, timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    img.save(os.path.join(folder, fileName), "JPEG")

def get_timelapse_frame_folders():
  folders = []
  folder = os.path.join(config_get("timelapse_folder"), "raw")
  for f in os.listdir(folder):
    if os.path.isdir(os.path.join(folder, f)):
      folders.append(f)
  folders.sort()
  return folders

def get_timelapse_frames_name(folder):
  frames = []
  folder = os.path.join(config_get("timelapse_folder"), "raw", folder)
  for f in os.listdir(folder):
    if os.path.isfile(os.path.join(folder, f)):
      frames.append(f)
  frames.sort()
  return frames

def get_timelapse_frame(folder, frame):
  path = os.path.join(config_get("timelapse_folder"), "raw", folder, frame)
  with open(path) as f:
    return f.read()

def get_timelapse_file(file):
  path = os.path.join(config_get("timelapse_folder"), file)
  with open(path) as f:
    return f.read()

def get_timelapses():
  timelapses = []
  folder = config_get("timelapse_folder")
  for f in os.listdir(folder):
    fpath = os.path.join(folder, f)
    if os.path.isfile(fpath):
      timelapses.append({
        "name": f,
        "size": os.stat(fpath).st_size,
      })
  return sorted(timelapses, key=lambda t: t.get("name"))

def clean_up():
  files = []
  size_tot = clean_up_subroutine(config_get("timelapse_folder"), files)
  size_max = config_get("timelapse_max_storage_volume") * 1024 * 1024

  if size_tot > size_max:
    sortedFiles = sorted(files, key=lambda f: f[0].st_mtime)
    for f in sortedFiles:
      os.remove(f[1])
      size_tot -= f[0].st_size
      if size_tot <= size_max:
        return

def clean_up_subroutine(folder, files):
  max_time = time.time() - config_get("timelapse_max_storage_time") * 3600 * 24
  size_tot = 0

  # will fail if the directory is not empty
  try:
    os.rmdir(folder)
  except: pass

  for f in os.listdir(folder):
    fpath = os.path.join(folder, f)
    if os.path.isfile(fpath):
      fstat = os.stat(fpath)
      if fstat.st_mtime < max_time:
        os.remove(fpath)
      else:
        size_tot += fstat.st_size
        files.append((fstat, fpath))
    elif os.path.isdir(fpath):
      size_tot += clean_up_subroutine(fpath, files)
  return size_tot

def get_frames_path_in_daterange(start, end):
  start = start.replace(':', '/')
  end = end.replace(':', '/')

  folders = filter(
    lambda f: f >= start[:10] and f <= end[:10],
    get_timelapse_frame_folders())

  allImages = []
  for folder in folders:
    allImages += map(lambda f: folder + "/" + f, get_timelapse_frames_name(folder))

  images = filter(
    lambda f: f >= start and f <= end,
    allImages
  )

  r = []
  for f in images:
    fpath = os.path.join(config_get("timelapse_folder"), "raw", f)
    if os.path.isfile(fpath):
      r.append(fpath)
  return r

def generate_timelapse(start, end, fileName=False):
  if not fileName:
    fileName = "timelapse_from_{0}_to_{1}_.m4v".format(start, end)

  outPath = os.path.join(config_get("timelapse_folder"), fileName)
  p = build_encoder(outPath)
  for fpath in get_frames_path_in_daterange(start, end):
    with open(fpath, 'r') as img:
      p.stdin.write(img.read())
  p.stdin.close()
  p.wait()

def generate_timelapse_overview(start, end, fileName=False):
  imgs = get_frames_path_in_daterange(start, end)
  if len(imgs) == 0:
    return

  from PIL import Image
  import math
  overview = False
  previousX = False
  stepWidth = False
  size = False

  for idx, imgPath in enumerate(imgs):
    if not overview:
      overview = Image.open(imgPath).copy()
      size = overview.size
      previousX = 0
      stepWidth = int(math.ceil(float(size[0]) / float(len(imgs))))
    else:
      x = int(math.ceil(float(size[0]) * idx / float(len(imgs))))
      if x != previousX:
        previousX = x
        img = Image.open(imgPath)
        if img.size == size:
          pos = (x, 0, x+stepWidth, size[1])
          img = img.crop(pos)
          overview.paste(img, pos)

  if not fileName:
    fileName = "timelapse_overview_from_{0}_to_{1}.jpg".format(start, end)
  outPath = os.path.join(config_get("timelapse_folder"), fileName)
  overview.save(outPath)

def build_encoder(outPath):
  from subprocess import Popen, PIPE
  encoder = config_get("timelapse_encoder")
  if encoder == "omxtx":
    return Popen(["omxtx", "-t", "mjpeg",
      "-b", "2m", "-r", config_get("timelapse_resolution"),
      "pipe:0", outPath],
      stdin=PIPE, shell=False)

  if encoder == "avconv":
    return Popen(['avconv', '-f', 'image2pipe',
      '-vcodec', 'mjpeg', '-r', config_get("timelapse_framerate"), '-i',
      '-', '-s', config_get("timelapse_resolution"),
      '-c:v', 'libx264', '-r', config_get("timelapse_framerate"), '-crf', '23', outPath],
      stdin=PIPE, shell=False)
  return False

def generate_night_timelapse():
  yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
  today = date.today().strftime('%Y-%m-%d')

  generate_timelapse(
    start="{0}/{1}".format(yesterday, "210000"),
    end="{0}/{1}".format(today, "070000"),
    fileName="{0}_night.m4v".format(yesterday)
  )

def generate_day_timelapse():
  today = date.today().strftime('%Y-%m-%d')

  generate_timelapse(
    start="{0}/{1}".format(today, "070000"),
    end="{0}/{1}".format(today, "190000"),
    fileName="{0}_day.m4v".format(today)
  )

def generate_daily_timelapse():
  yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
  today = date.today().strftime('%Y-%m-%d')

  generate_timelapse(
    start="{0}/{1}".format(yesterday, "000000"),
    end="{0}/{1}".format(today, "000000"),
    fileName="{0}_24h.m4v".format(yesterday)
  )

def refresh_timelapse_schedule():
  try:
    sched.unschedule_func(take_timelapse_picture)
  except: pass
  sched.add_interval_job(take_timelapse_picture,
    seconds=config_get("timelapse_frame_interval"),
    name="capture_frame",
    max_instances=1)

  try:
    sched.unschedule_func(clean_up)
  except: pass
  sched.add_interval_job(clean_up,
    minutes=60,
    name="clean_up",
    max_instances=1)

  try:
    sched.unschedule_func(generate_night_timelapse)
  except: pass
  sched.add_interval_job(generate_night_timelapse,
    days=1,
    name="generate_night_timelapse",
    start_date="{0} 07:01:00".format(date.today().strftime('%Y-%m-%d')),
    max_instances=1)

  try:
    sched.unschedule_func(generate_day_timelapse)
  except: pass
  sched.add_interval_job(generate_day_timelapse,
    days=1,
    name="generate_day_timelapse",
    start_date="{0} 19:01:00".format(date.today().strftime('%Y-%m-%d')),
    max_instances=1)

  try:
    sched.unschedule_func(generate_daily_timelapse)
  except: pass
  sched.add_interval_job(generate_daily_timelapse,
    days=1,
    name="generate_daily_timelapse",
    start_date="{0} 00:01:00".format((date.today() + timedelta(days=1)).strftime('%Y-%m-%d')),
    max_instances=1)

from flask import Blueprint, render_template, make_response
from auth import *

timelapse_cgi = Blueprint('timelapse_cgi', __name__, template_folder='templates/timelapse')
refresh_timelapse_schedule()

def is_path_sane(path):
  return not path.startswith(".") and "/" not in path and "\\" not in path

@timelapse_cgi.route("/timelapse")
@requires_auth
def timelapse_home():
  jobs = []
  for job in sched.get_jobs():
    jobs.append({
      "name": job.name,
      "interval": job.trigger.interval,
      "next_run": job.trigger.get_next_fire_time(datetime.now()) - datetime.now(),
      "max_runs": job.max_runs,
      "total_runs": job.runs
    })

  return render_template("timelapse/index.html",
    jobs=jobs,
    timelapses=get_timelapses(),
    frame_folders=get_timelapse_frame_folders())

@timelapse_cgi.route("/timelapse/frame/<folder>")
@requires_auth
def timelapse_frames(folder):
  if not is_path_sane(folder):
    return abort(make_response("Invalid folder name", 400))

  return render_template("timelapse/frames.html",
    folder=folder,
    frames=get_timelapse_frames_name(folder))

@timelapse_cgi.route("/timelapse/view/<file>")
@requires_auth
def timelapse_view(file):
  if not is_path_sane(file):
    return abort(make_response("Invalid file name", 400))
  return render_template("timelapse/play.html",
    timelapse_file=file)

@timelapse_cgi.route("/timelapse/create/overview/<start>/<end>")
@requires_auth
def timelapse_create_overview(start, end):
  sched.add_interval_job(generate_timelapse_overview,
    name="manual_generate_timelapse_overview",
    max_runs=1,
    args=[start, end])
  return "Ok!"

@timelapse_cgi.route("/timelapse/create/<start>/<end>")
@requires_auth
def timelapse_create(start, end):
  sched.add_interval_job(generate_timelapse,
    name="manual_generate_timelapse",
    max_runs=1,
    args=[start, end])
  return "Ok!"