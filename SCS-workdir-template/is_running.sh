#!/bin/bash

#Query scs process
ps aux | grep $USER | grep $(cat PID)
