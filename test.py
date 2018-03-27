import subprocess, re, time, codecs, sys, json
DEBUG = False

sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)

prop_mapping = {
  'serialno': 'ro.serialno',
  'make': 'ro.product.brand',
  'model': 'ro.svp.modelname',
  'series': 'ro.svp.modelseries',
  'ipaddress': 'dhcp.wlan0.ipaddress',
  'panelsize': 'ro.svp.panel_inch'
}

def load_report(filename):
  f = open(filename, 'r')
  json.loads(f.read())
  f.close()

def save_report(filename, report):
  f = open(filename, 'w')
  f.write(report)
  f.close()


def execute(cmd):
  if DEBUG:
    # pass
    print("#### ===> EXECUTING " + " ".join(cmd))
  out = subprocess.check_output(cmd)
  return out.decode('utf-8')

def adb(serial, cmd):
  return execute(f'adb -s {serial} {cmd}'.split(" "))

def connect(serial, port=5555):
  status = execute(f'adb connect {serial}:{port}'.split(" "))
  return (not(status.find("unable") > -1))

def get_package_ver(serial, package):
  raw = adb(serial, f'shell dumpsys package {package.strip()} | grep versionName')
  return raw[raw.find("=")+1:].strip()


def process_app(serial, app_data, count):
  i = app_data[0]
  app_data = app_data[1].strip()
  app_data = app_data.replace("package:", "")
  info = app_data.split("=")
  update_progress((i / count) * 100, f'Processing app: {info[1]}... ')
  version = get_package_ver(serial, info[1])
  return { "apk": info[0], "package": info[1], "version": version }



def get_apps(serial):
  raw = execute(f'adb -s {serial} shell pm list packages -f'.split(" ")).split("\n")
  count = len(raw)
  out = {}
  apps = filter(lambda x: x != "", raw)
  apps = list(map(lambda x: process_app(serial, x, count), enumerate(apps)))
  for app in apps:
    out[app["package"]] = { "apk": app["apk"], "package": app["package"], "version": app["version"] }
  return out



def update_progress(percent, msg=None):
  app.queueFunction(app.setMeter, "progress", percent, msg + " (" + "%.3g" % round(percent) + "%)")



def get_device_prop(serial):
  raw = execute(f'adb -s {serial} shell getprop'.split(" "))
  raw = raw.split("\n")
  out = {}
  for entry in raw:
    if(entry):
      key, value = entry.strip().split(": ")
      out[key[1:-1]] = value[1:-1]
  return out


def send_key_event(serial, event_id):
  try:
    raw = execute(f'adb -s {serial} shell input keyevent {event_id}'.split(" "))
    return True
  except Exception as e:
    print(e)
    return False


def is_device_awake(serial):
  data = get_device_awake_state(serial)
  out = ((data["display"] == "ON") and (data["wakefulness"] == "Awake"))
  return out


def get_device_awake_state(serial):
  raw = execute(['adb', '-s', serial, 'shell', 'dumpsys power | grep -e "mWakefulness=" -e "Display Power"']).strip().split("\n")
  out = {}
  for line in raw:
    if line.startswith("Display"):
      out["display"] = line.strip().split("=")[-1]
    elif line.startswith("mWakefulness"):
      out["wakefulness"] = line.strip().split("=")[-1]
  return out


def get_devices():
  raw = execute("adb devices".split(" "))
  raw = raw.split("\n")
  raw.pop(0)
  raw = list(filter(lambda e: e.strip() != '', raw))
  raw = list(map(lambda x: x.split("\t")[0], raw))
  return raw


def gen_report(ip):
  connect(ip)
  devices = get_devices()
  report = {}
  for device in devices:
    if not(is_device_awake(device)):
      print("DEVICE IS OFF, POWERING ON...")
      send_key_event(device, 26)
      attempts = 10
      while not(is_device_awake(device)) and (attempts > 0):
        attempts -= 1
        time.sleep(1)
        status = get_device_awake_state(device)
      if is_device_awake(device):
        print("DEVICE IS ON")

    props = get_device_prop(device)

    report[device] = {}
    count = len(prop_mapping)
    i = 0
    for k, v in prop_mapping.items():
      i += 1
      report[device][k] = props.get(v, None)
    report[device]['apps'] = get_apps(device)
    update_progress(100, "Done!")
    # report[device]["model"] = props["ro.svp.modelname"]
    # print(report) ## TODO: draw actual report
    serial = report[device]['serialno']
    report[serial] = report.pop(device)
    out = json.dumps(report, indent=4)
    # print(out)
    last_report = load_report("report.json")
    save_report("report.json", out)
    for app_i, app in enumerate(report[serial]['apps']):
      # print(app)
      add_app_entry(report[serial]['apps'][app], app_i)


def add_app_entry(app_data={}, row=0):
  if type(row) is not int:
    print("zomg row is not a fucking int for some fucking reason fffffuuuudsfglkdfgn\n" + str(type(row)) + " " + str(row))
  print("row is a " + str(type(row)) + " whose value is '" + str(row) + "'")
  app.openScrollPane("app_report")
  app.setSticky("ew")
  app.addLabel("name_"+app_data["package"], row=row, column=0)
  app.addLabel("ver_"+app_data["version"], row=row, column=1)
  app.addButton("open_"+app_data["version"], None, row=row, column=2)
  app.stopScrollPane()


def threadulate(func):
  app.thread(func)


# import the library
from appJar import gui

app = gui("Betsy's Artisanal Android TV Tools, Yes!", "700x500")
app.setFont(15)
app.setLocation("CENTER")
app.setIcon('./baatty.gif')

app.setSticky("new")

app.addLabelEntry("ip address", row=0, column=0)
app.setEntry("ip address", "172.30.7.97")
app.addButton("Yoink!", lambda: threadulate(gen_report(app.getEntry("ip address"))), row=0, column=1)
app.setSticky("news")
app.startScrollPane("app_report")
app.stopScrollPane()

app.setSticky("sew")
app.addMeter("progress", colspan=2)
app.setMeterFill("progress", "blue")
app.setMeterBg("progress", "black")
app.setMeterFg("progress", "gold")



app.go()

