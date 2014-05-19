#!/usr/bin/env python
import json
import sys

if __name__ == '__main__':
    first_item = True
    line = True
    print "["
    while line:
        line = sys.stdin.readline()
        if not line:
            continue
        if line[0] == '!':
            continue
        if first_item:
            first_item = False
        else:
            print ","
        res = line.split(' ')
        res[4] = res[4].replace('\n', '')
        if res[3] == '-':
            res[3] = -1
        if res[4] == '-':
            res[4] = -1
        sys.stdout.write(json.dumps( { 'ts': float(res[0]), 'protocol':res[1], 'length':int(res[2]), 'source_port':int(res[3]), 'dest_port':int(res[4]) } ))
    print "]"

