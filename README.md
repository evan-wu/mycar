mycar
----
A self-driving car project for beginners and practitioners.

Build on RC car and jetson nano.

# Topic 4: Visual PID line follower

[blog article](https://blog.csdn.net/evanwoods/)

1. connect your bluetooth joystick.

2. then run the code:

```shell script
git clone https://github.com/evan-wu/mycar.git --branch blog-5 --single-branch
pip3 instal pyyaml adafruit-circuitpython-servokit flask pyzmq
chmod +x bin/run.sh
bin/run.sh config/joystick_drive.yml 120
```

Use joystick to navigate, happy driving!