#!/usr/bin/python

##########################################################################
#  Mellanox FCA checker                                                  #
#                                                                        #
#  Copyright (C) 2017 EDF S.A.                                           #
#  Contact: CCN-HPC <dsp-cspit-ccn-hpc@edf.fr>                           #
#                                                                        #
#  This program is free software; you can redistribute in and/or         #
#  modify it under the terms of the GNU General Public License,          #
#  version 2, as published by the Free Software Foundation.              #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
##########################################################################

import socket
import subprocess
import time
import sys
import os
import re

banner ="python fca_checker.py PATH_REDUCE_TEST LOCAL_IB_IP [FCA_PATH]"
fca_error = { 'fca_cli': 0, 'fca_fmm': 1, 'fca_bench': 1}

if len(sys.argv)<3:
    sys.stderr.write('Parameter error\n')
    sys.stderr.write(banner+'\n')
    sys.exit(1)

if len(sys.argv)>3:
    fca_path = sys.argv[3]
else:
    fca_path = "/opt/mellanox/fca/"

fmm_cmd=os.path.join(fca_path,"bin/fca_find_fmm")

bench_path = sys.argv[1]
local_ib_ip = sys.argv[2]

## simple ipv4 regex check
ip = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

if not ip.match(local_ib_ip):
    sys.stderr.write('Invalid parameter: second parameter has to be a valid IPv4 address\n')
    sys.stderr.write(banner+'\n')
    sys.exit(1)


fmm_expected_answer = "FMM replied from"
server_cmd = [bench_path,'-s','--rank','0','--comm-size','2']
client_cmd = [bench_path, '-c',local_ib_ip,'--rank','1','--comm-size','2']
env = {}
env["LD_LIBRARY_PATH"]="$LD_LIBRARY_PATH:{0}/lib/".format(fca_path)

## Test FCA telnet CLI

print "Testing FCA telnet CLI ..."

clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.settimeout(2)
try:
    clientsocket.connect(('127.0.0.1', 2345))
except:
    sys.stderr.write('Unable to connect to FCA telnet CLI\n')
    fca_error['fca_cli'] = 1

if not fca_error['fca_cli']:
    print 'FCA telnet CLI is up'

## Test whether FMM is up

print "Testing FCA FMM ..."

fmm_process = subprocess.Popen(fmm_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

for line in fmm_process.stdout.readlines():
    if fmm_expected_answer in line:
        fca_error['fca_fmm']=0
    print line

if not fca_error['fca_fmm']:
    print 'FCA FMM is up'

## Test with benchmark

server = subprocess.Popen(server_cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
client = subprocess.Popen(client_cmd, env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

time.sleep(3)

error_s = 1
error_c = 1

while not client.poll():
    print "Benchmark client still running, killing... "
    time.sleep(1)
    client.kill()

if client.poll():
    print "Benchmark client has terminated"
    for line in client.stdout.readlines():
        print line
        error_c=0

while not server.poll():
    print "Benchmark server still running, killing... "
    time.sleep(1)
    server.kill()

if server.poll():
    print "Benchmark server has terminated"
    for line in server.stdout.readlines():
        print line
        error_s=0

fca_error['fca_bench'] = error_c | error_s

if not fca_error['fca_bench']:
    print "Benchmark created a FCA comunicator succesfully"
else:
    sys.stderr.write('Unable to run the FCA benchmark\n')

print "Tests results: " + str(fca_error)

if sum(fca_error.values()) > 0:
    sys.exit(1)
