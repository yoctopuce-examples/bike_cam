# Bike Cam

This python script detect passage of a bike and trigger a camera recording for a given length of time. 
For more details read our blog post : https://www.yoctopuce.com/EN/article/detecting-and-filming-the-passage-of-a-bike


To detect the bike we use a Yocto-3D-V2 glued to a 2mm aluminum slider. When the bike pass on the slider the
the vibration are detected by the Yocto-3D-V2 and the script start the recording. For now, the only supported 
camera is a Garmin Virb Ultra 30. If a Yocto-Buzzer is connected, the script emit a small beep when the recording
is started.

![The system is composed of a Yocto-3D-V2, a Yocto-Buzzer, a Raspberry Pi, and a Garmin camera](https://www.yoctopuce.com/pubarchive/2018-09/big_picture_1.png)

The system is composed of a Yocto-3D-V2, a Yocto-Buzzer, a Raspberry Pi, and a Garmin camera
