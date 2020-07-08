mycar
----
A self-driving car project for beginners and practitioners.

Build on RC car and jetson nano.

# At a glance:
## Assembled Car
![Assembled Car](https://img-blog.csdnimg.cn/20200619101956348.jpg?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L2V2YW53b29kcw==,size_16,color_FFFFFF,t_70)

## Code UML
![Class Diagram](https://img-blog.csdnimg.cn/20200702184447668.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L2V2YW53b29kcw==,size_16,color_FFFFFF,t_70)
`Note: This is the initial design, may not reflect the code now`

## A Web UI
![Web Driving UI](https://img-blog.csdnimg.cn/20200701161319835.gif)

# How to Run:

```shell script
git clone https://github.com/evan-wu/mycar.git
cd mycar
pip3 instal pyyaml adafruit-circuitpython-servokit flask pyzmq
chmod +x bin/run.sh
bin/run.sh <config_file, e.g.: config/web_drive.yml> <time_to_stop, e.g.: 120>
```

Happy and safe driving!

# A Series of Introduction (More is coming...):

## Topic 1: Getting Started
[blog article](https://blog.csdn.net/evanwoods/article/details/106548239)

## Topic 2: Hardware Parts
[blog article](https://blog.csdn.net/evanwoods/article/details/106850925)

## Topic 3: Web Driving
[blog article](https://blog.csdn.net/evanwoods/article/details/107066042)

## Topic 4: Joystick Driving
[blog article](https://blog.csdn.net/evanwoods/article/details/107116882)

