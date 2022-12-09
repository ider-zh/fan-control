#!/usr/bin/python3
#!python

# this script is for r730xd x2 server to down fan speed,
# not find query fan speed way
# strategy
# (cpu 2400) or (temp up 65 and fan up 40) use auto
import psutil
import time
import os
import datetime
import re

TOP_CPU_USAGE = 40
LOW_CPU_USAGE = 20

TOP_CPU_TEMP = 62
LOWER_CPU_TEMP = 57

MIN_FAN_SPEED = 15
# exceed MAX_MANUAL_FAN_SPEED then use auto control
MAX_MANUAL_FAN_SPEED = 35

SYSTEM_STATUS = {
    "auto": False,
    "fan_speed": 0,
}

# two cpu
def get_cpu_temp():
    paths = ['/sys/class/thermal/thermal_zone0/temp','/sys/class/thermal/thermal_zone1/temp']
    max_temp = 0
    for _ in range(3):
        for path in paths:
            with open(path,'rt')as f:
                temp = f.read()
                max_temp = max(int(temp.strip()),max_temp)
        time.sleep(1)
    return int(max_temp/1000)
        
def get_cpu_usage():
    # max 4800
    return psutil.cpu_percent(3)

def set_fan_speed(speed:int):
    if SYSTEM_STATUS["fan_speed"] == speed:
        return
    print(get_time_str(), " set fan to:", speed)
    SYSTEM_STATUS['fan_speed'] = speed
    os.system(f"sudo ipmitool raw 0x30 0x30 0x02 0xff {hex(speed)}")

def switch_pmi_status(status:bool, init=False):
    if not init and SYSTEM_STATUS["auto"] == status:
        return

    SYSTEM_STATUS["auto"] = status
    print(get_time_str()," switch to:", status)
    if status:
        # open
        os.system("sudo ipmitool raw 0x30 0x30 0x01 0x01")
    else:
        # close
        os.system("sudo ipmitool raw 0x30 0x30 0x01 0x00")

def get_ipmi_status():
    ret = os.popen("sudo ipmitool sdr list full")
    data = ret.read()
    mt = re.findall(r" (\d+) RPM",data)
    mti = list(map(lambda s:int(s),mt))
    average_fan_speed = int(sum(mti)/len(mti))

    mt = re.findall(r"^Temp.*? (\d+) degrees",data,re.M)
    mti = list(map(lambda s:int(s),mt))
    average_cpu_temp = int(sum(mti)/len(mti))

    mt = re.findall(r"^CPU.*? (\d+) percent",data,re.M)
    mti = list(map(lambda s:int(s),mt))
    average_cpu_usage = int(sum(mti)/len(mti))

    return average_fan_speed,average_cpu_temp,average_cpu_usage

def init():
    usage = get_cpu_usage()
    temp = get_cpu_temp()
    if usage > TOP_CPU_USAGE and temp > TOP_CPU_TEMP:
        switch_pmi_status(True, init=True)
        return

    switch_pmi_status(False, init=True)
    if LOWER_CPU_TEMP < temp < TOP_CPU_TEMP:
        set_fan_speed(MAX_MANUAL_FAN_SPEED)
    elif temp < LOWER_CPU_TEMP:
        set_fan_speed(MIN_FAN_SPEED)

def get_time_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    time.sleep(5)
    while 1:
        # usage = get_cpu_usage()
        # temp = get_cpu_temp()
        fan_speed , temp,usage = get_ipmi_status()
        print(f'{get_time_str()} CPU:{usage} temp:{temp} fan_speed:{fan_speed}',end="\r")
        if usage > TOP_CPU_USAGE and temp > TOP_CPU_TEMP:
            # up up up 
            switch_pmi_status(True)
            time.sleep(120)
        elif temp > TOP_CPU_TEMP:
            #  up up up
            if SYSTEM_STATUS["fan_speed"] + 5 < MAX_MANUAL_FAN_SPEED:
                switch_pmi_status(False)
                set_fan_speed(SYSTEM_STATUS["fan_speed"] + 5)
                time.sleep(30)
            else:
                switch_pmi_status(True)
                time.sleep(60)
        elif usage <= LOW_CPU_USAGE and temp < LOWER_CPU_TEMP:
            # down
            switch_pmi_status(False)
            set_fan_speed(MIN_FAN_SPEED)
            time.sleep(30)
        else:
            # keep hold
            time.sleep(30)
            pass

if __name__ == "__main__":
    init()
    main()


# sudo ipmitool sdr list full