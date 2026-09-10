import sys
import numpy as np, rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

class Grab(Node):
    def __init__(self):
        super().__init__("grab")
        self.got = False
        self.create_subscription(Image, "/probe_cam", self.cb, 10)
    def cb(self, msg):
        if self.got: return
        a = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
        print(f"frame {msg.width}x{msg.height} enc={msg.encoding}")
        print(f"  mean={a.mean():.1f} min={a.min()} max={a.max()} std={a.std():.1f}")
        print("  VERDICT:", "REAL PIXELS" if a.std() > 3 else "BLANK/BLACK — rendering failed")
        self.got = True

rclpy.init()
n = Grab()
import time
t0 = time.time()
while rclpy.ok() and not n.got and time.time() - t0 < 25:
    rclpy.spin_once(n, timeout_sec=0.5)
if not n.got: print("NO FRAME RECEIVED")
rclpy.shutdown()
