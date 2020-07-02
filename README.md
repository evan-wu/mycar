----
mycar
----
A self-driving car project for beginners and practitioners.

Build on RC car and jetson nano.

# Topic 3: Web Driving

![Web Driving UI](https://img-blog.csdnimg.cn/20200701161319835.gif)

![Class Diagram](https://img-blog.csdnimg.cn/20200702184447668.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L2V2YW53b29kcw==,size_16,color_FFFFFF,t_70)

[blog article](https://blog.csdn.net/evanwoods/article/details/107066042)

```shell script
git clone https://github.com/evan-wu/mycar.git --branch blog-3 --single-branch
pip3 instal pyyaml adafruit-circuitpython-servokit flask pyzmq
chmod +x bin/run.sh
bin/run.sh config/web_drive.yml 120
```

then use a browser to navigate to `http://<jetson nano ip>:8080`, happy driving!