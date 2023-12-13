#!/bin/bash
wireshark -Xlua_script:quickbusDissector.lua $*
