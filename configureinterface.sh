#!/bin/bash

ifconfig can0 down
ip link set can0 type can bitrate 62000
ifconfig can0 up

candump -n 9 can0
