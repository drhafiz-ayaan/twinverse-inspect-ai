# Simulation

A virtual inspection world, so the system can be validated against ground truth
we control rather than against public datasets we can only hope are labelled
correctly.

## Why this is worth building

The dashboard's 3D viewer carries a caveat today: *"Illustrative placement, not
a survey — nothing in the pipeline recovers where a photo was taken from."* In
simulation the camera pose is **known exactly**, so marker placement stops being
illustrative and becomes measurable. The weakest claim in the product turns into
the strongest one.

It also produces numbers no public dataset can give us: how detection degrades
with standoff distance, viewing angle and lighting, measured against cracks
whose size and position we set ourselves.

## Verified working on this machine

Gazebo Harmonic 8.11 and ROS 2 Jazzy are installed, and **headless camera
rendering is confirmed** — real pixels, not a black frame:

```bash
# terminal 1
source /opt/ros/jazzy/setup.bash
gz sim -s -r --headless-rendering sim/worlds/smoke_camera.sdf

# terminal 2
source /opt/ros/jazzy/setup.bash
ros2 run ros_gz_image image_bridge /probe_cam &
/usr/bin/python3 sim/smoke_check.py       # expects "REAL PIXELS"
```

Three things that will bite anyone repeating this:

- **`gz` needs the ROS environment sourced.** Without it the vendored binary
  cannot find its own plugins and reports *"I cannot find any available 'gz'
  command"*, which reads like a missing install rather than a missing variable.
- **Use `/usr/bin/python3`, not the project venv.** `rclpy` is installed against
  the system interpreter, and the venv shadows it.
- **Do not stop these with `pkill -f "gz sim"`.** The pattern matches the shell
  running the command, so it kills the caller. Match on the executable path
  instead.

`libEGL warning: egl: failed to create dri2 screen` appears in the log and is
harmless — rendering falls through to a working path.

## Design

The simulated drone **uploads to the existing API over HTTP**, exactly as a real
drone would. It does not import the detector or touch the database.

That single choice does three things: it sidesteps the ROS/venv interpreter
split, it exercises the real ingest → detection → severity → report path rather
than a parallel copy of it, and it means anything proven in simulation is proven
about the shipped system.

Ground-truth crack poses are written alongside each world so a run can be scored
after the fact.
