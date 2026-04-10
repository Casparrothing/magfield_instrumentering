import socket
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B

large = LargeMotor(OUTPUT_A)
medium = MediumMotor(OUTPUT_B)

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 5000))
s.listen(1)

while True:
    print("Waiting for connection...")
    conn, addr = s.accept()
    print("Connected from " + str(addr))
    try:
        while True:
            cmd = conn.recv(1024).decode().strip()
            if not cmd:
                break
            parts = cmd.split()
            name = parts[0]
            arg = float(parts[1]) if len(parts) > 1 else 50

            if name == 'spin_start':
                medium.on(arg)
            elif name == 'spin_stop':
                medium.off()
            elif name == 'get_angle':
                angle = str(medium.position)
                conn.send((angle + '\n').encode())
            elif name == 'reset_angle':
                medium.position = 0
                conn.send(b'ok\n')
            elif name == 'step':
                large.on_for_degrees(arg, 10, brake=True, block=True)
            elif name == 'step_back':
                large.on_for_degrees(arg, -10, brake=True, block=True)
            elif name == 'quit':
                large.off()
                medium.off()
                conn.close()
                s.close()
                exit()
    except Exception as e:
        print("Error: " + str(e))
    finally:
        large.off()
        medium.off()
        conn.close()