#!/usr/bin/python
import sys
import requests
from datetime import datetime
import time
import monitoring
import pprint

PARAMS = {}
SERVICESURL = "/api/v1/service/"
ALREADYSEND = {}

def list_services_url(services, servicesUrl):
    session = requests.Session()
    headers = {"Authorization": PARAMS.get('APIAUTH')}
    for service in services.get("objects", []):
        prefixName = service["name"].split("-")
        now = time.time() + time.altzone
        deployedTime = time.mktime(time.strptime(service["deployed_datetime"], "%a, %d %b %Y %H:%M:%S +0000"))
        if service["started_datetime"]:
            deployedTime = time.mktime(time.strptime(service["started_datetime"], "%a, %d %b %Y %H:%M:%S +0000"))
        diff = now - deployedTime
        if prefixName[0] == "APACHE" and diff > 900 and service["state"] != "Redeploying":
            servicesUrl.append(service["resource_uri"])
    meta = services.get("meta")
    next = meta["next"]
    if next:
        r = session.get(PARAMS.get('TUTUMURL') + next, headers=headers)
        r.raise_for_status()
        nextServices = r.json()
        list_services_url(nextServices, servicesUrl)

    return servicesUrl

def get_vhosts(servicesUrl):
    session = requests.Session()
    headers = {"Authorization": PARAMS.get('APIAUTH')}
    vhosts = []
    for serviceUrl in servicesUrl:
        current_vhosts = []
        dont_monitor = False
        vhost_to_exclude = []
        r = session.get(PARAMS.get('TUTUMURL') + serviceUrl, headers=headers)
        r.raise_for_status()
        service = r.json()
        for env in service.get("container_envvars"):
            if env["key"] == "VIRTUAL_HOST":
                for vhost in env["value"].split(':'):
                    if vhost == "demo.rubedo-project.org" or vhost == "demoadmin.rubedo-project.org":
                        if datetime.now().minute > 57 or datetime.now().minute < 8:
                            continue
                    current_vhosts.append(vhost)
            if env["key"] == "DONT_MONITOR":
                if env["value"] == "true":
                    dont_monitor = True
                else:
                    vhost_to_exclude = env["value"].split(',')
        for vhost in current_vhosts:
            if not dont_monitor and not vhost in vhost_to_exclude:
                vhosts.append(vhost)
    return vhosts

def request(vhost):
    notresponding = False
    arguments = {}
    try:
        session = requests.Session()
        r = session.get("http://" + vhost, timeout=20)
        r.raise_for_status()
    except requests.RequestException, args:
        arguments = args
        notresponding = True
    return notresponding, arguments

def check_status(vhosts):
    vhosts_fail = {}
    for vhost in vhosts:
        send = True
        if vhost in ALREADYSEND:
            if (time.time() - ALREADYSEND[vhost]) < 18000:
                send = False
        if send:
            notresponding, argts = request(vhost)
            if notresponding:
                ntres,args = request(vhost)
                if ntres:
                    ALREADYSEND[vhost] = time.time()
                    print("Send an email")
                    vhosts_fail[vhost] = pprint.pformat(args.args)
    return vhosts_fail

def main(parms):
    global PARAMS
    config = monitoring.checkconfig(parms)
    PARAMS = monitoring.loadconfig(config)
    while True:
        session = requests.Session()
        headers = {"Authorization": PARAMS.get('APIAUTH')}
        r = session.get(PARAMS.get('TUTUMURL') + SERVICESURL, headers=headers)
        r.raise_for_status()
        services = r.json()
        servicesUrl = list_services_url(services, [])
        vhosts = get_vhosts(servicesUrl)
        if PARAMS.get("MANUAL_URL"):
            vhosts = vhosts + PARAMS.get("MANUAL_URL")
        vhosts_fails = check_status(vhosts)
        if vhosts_fails:
            monitoring.send_mail_vhost(vhosts_fails)
        time.sleep(180)

if __name__ == "__main__":
    main(sys.argv[1:])

