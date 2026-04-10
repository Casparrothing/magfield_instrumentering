import serial
import serial.tools.list_ports
import socket
import time
import math
import numpy as np
import matplotlib.pyplot as plt
import threading

BAUDRATE = 9600
OUTPUT_FILE = "magnetic_field_2d.txt"
EV3_IP = "192.168.2.3"
EV3_PORT = 5000

RADIAL_STEPS = 25
SETTLE_TIME = 0.5
MOTOR_SPEED = 10
SAMPLES_PER_POINT = 1
GEAR_RATIO = 1.66

# ---------- Find Arduino ----------
def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        desc = (port.description or "").lower()
        device = (port.device or "").lower()
        if "arduino" in desc or "usbmodem" in device or "usbserial" in device:
            return port.device
    usb_ports = [p.device for p in ports if "usb" in p.device.lower()]
    if len(usb_ports) == 1:
        return usb_ports[0]
    raise RuntimeError("Could not find Arduino port automatically.")

# ---------- Connect ----------
port = find_arduino_port()
print(f"Connecting to Arduino on {port} ...")
ser = serial.Serial(port, BAUDRATE, timeout=1)
time.sleep(2)
print("Arduino connected.")

print(f"Connecting to EV3 at {EV3_IP}:{EV3_PORT} ...")
ev3 = socket.socket()
ev3.connect((EV3_IP, EV3_PORT))
print("EV3 connected.\n")

ev3_lock = threading.Lock()

def send_ev3(cmd):
    with ev3_lock:
        ev3.send((cmd + "\n").encode())
        time.sleep(0.02)

def get_angle():
    with ev3_lock:
        ev3.send(b"get_angle\n")
        try:
            response = ev3.recv(64).decode().strip()
            return float(response)
        except:
            return None

# ---------- Read one magnetic field measurement ----------
MAX_FIELD = 30  # discard any reading with |gx|, |gy|, or |gz| above this

def read_field(n=SAMPLES_PER_POINT):
    samples = []
    while len(samples) < n:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            parts = line.split(",")
            if len(parts) != 3:
                continue
            gx, gy, gz = float(parts[0]), float(parts[1]), float(parts[2])
            if abs(gx) > MAX_FIELD or abs(gy) > MAX_FIELD or abs(gz) > MAX_FIELD:
                print(f"  Outlier discarded: gx={gx}, gy={gy}, gz={gz}")
                continue
            samples.append((gx, gy, gz))
        except Exception:
            continue
    gx = sum(s[0] for s in samples) / n
    gy = sum(s[1] for s in samples) / n
    gz = sum(s[2] for s in samples) / n
    return gx, gy, gz

# ---------- Setup live plot ----------
plt.ion()
fig = plt.figure(figsize=(13, 6))
ax1 = fig.add_subplot(121, projection='polar')
ax2 = fig.add_subplot(122)
progress_text = fig.text(0.5, 0.02, "", ha='center', fontsize=10, color='gray')

all_data = [[] for _ in range(RADIAL_STEPS)]

def update_plot(current_r):
    ax1.cla()
    ax2.cla()
    ax1.set_title("Magnetic field (polar)")
    ax2.set_title("Magnetic field (cartesian)")
    ax2.set_aspect('equal')
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")

    all_bmags = [d[1] for r in range(current_r + 1) for d in all_data[r]]
    if not all_bmags:
        return
    vmin, vmax = min(all_bmags), max(all_bmags)
    if vmin == vmax:
        vmax = vmin + 1

    all_angles, all_radii, all_vals = [], [], []
    for r_idx in range(current_r + 1):
        data = all_data[r_idx]
        if not data:
            continue
        for angle_rad, bmag in data:
            all_angles.append(angle_rad)
            all_radii.append(r_idx + 1)
            all_vals.append(bmag)

    if len(all_vals) < 10:
        return

    from scipy.interpolate import griddata

    xs = np.array(all_radii) * np.cos(all_angles)
    ys = np.array(all_radii) * np.sin(all_angles)
    zs = np.array(all_vals)

    # Cartesian scatter
    sc = ax2.scatter(xs, ys, c=zs, cmap='plasma', s=20, vmin=vmin, vmax=vmax)

    # Polar contourf
    if current_r < 1:
        return
    try:
        grid_r = np.linspace(1, current_r + 1, current_r + 1)
        grid_a = np.linspace(0, 2 * np.pi, 360)
        Ag, Rg = np.meshgrid(grid_a, grid_r)
        xg = Rg * np.cos(Ag)
        yg = Rg * np.sin(Ag)
        method = 'cubic' if len(zs) > 50 else 'linear'
        Zg = griddata((xs, ys), zs, (xg, yg), method=method)
        cf = ax1.contourf(Ag, Rg, Zg, levels=20, cmap='plasma', vmin=vmin, vmax=vmax)
    except Exception:
        pass

    total_points = sum(len(all_data[r]) for r in range(RADIAL_STEPS))
    progress_text.set_text(f"Radial step {current_r + 1}/{RADIAL_STEPS} — {total_points} points collected")

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.canvas.draw()
    fig.canvas.flush_events()

# ---------- Scan ----------
print(f"Starting scan: {RADIAL_STEPS} radial steps, continuous 360° rotation per step")
print("Press Ctrl+C to abort.\n")

with open(OUTPUT_FILE, "w") as f:
    f.write("radial_step,angle_deg,gx,gy,gz,bmag\n")

    try:
        for r in range(RADIAL_STEPS):
            print(f"Radial step {r+1}/{RADIAL_STEPS} — spinning...")

            # Reset and start spin
            with ev3_lock:
                ev3.send(b"reset_angle\n")
                ev3.recv(64)

            send_ev3(f"spin_start {MOTOR_SPEED}")
            

            # Collect samples until motor reaches 360°
            samples = []
            while True:
                gx, gy, gz = read_field()
                samples.append((gx, gy, gz))

                # Check angle in main thread, no background watcher needed
                with ev3_lock:
                    ev3.send(b"get_angle\n")
                    try:
                        response = ev3.recv(64).decode().strip()
                        angle = float(response)
                    except:
                        angle = 0.0

                if angle >= 360*GEAR_RATIO:
                    send_ev3("spin_stop")
                    break

            # Distribute samples evenly over 0–360°
            n = len(samples)
            for i, (gx, gy, gz) in enumerate(samples):
                angle_deg = 360.0 * i / n
                angle_rad = math.radians(angle_deg)
                bmag = math.sqrt(gx**2 + gy**2 + gz**2)
                all_data[r].append((angle_rad, bmag))
                f.write(f"{r},{angle_deg:.2f},{gx:.6f},{gy:.6f},{gz:.6f},{bmag:.6f}\n")
            f.flush()

            print(f"  Collected {n} points")
            update_plot(r)

            time.sleep(SETTLE_TIME)
            if r < RADIAL_STEPS - 1:
                send_ev3(f"step_back {MOTOR_SPEED}")
                time.sleep(SETTLE_TIME)

    except KeyboardInterrupt:
        print("\nScan aborted.")
        send_ev3("spin_stop")

print("\nScan complete!")

# Return radial arm to start
print("Returning radial arm to start...")
for _ in range(RADIAL_STEPS + 1):
    send_ev3(f"step {MOTOR_SPEED}")
    time.sleep(SETTLE_TIME)


plt.ioff()
update_plot(RADIAL_STEPS-1)
plt.savefig("magnetic_field_2d.png", dpi=150)
plt.show()

send_ev3("quit")
ev3.close()
ser.close()
print("Saved to", OUTPUT_FILE)