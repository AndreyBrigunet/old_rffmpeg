#!/usr/bin/env python
import time
from time import sleep
import psutil
import os


# while True:
#     cpu = psutil.cpu_percent()
#     print (cpu)
#     if cpu  > 12:
#         print("mai mare ca 10")
#     sleep(0.5)
#     os.system('clear')

_, cpu_percent, _ = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]

print(_)


# with open('yourfile.txt', "a") as myfile:
#     myfile.write(str(psutil.cpu_percent(interval=10))+"%"'\n')
