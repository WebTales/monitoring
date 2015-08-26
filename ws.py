#!/usr/bin/python
import sys
import websocket
import json
import requests
import monitoring
import pprint

PARAMS = {}

def get_logs(uuid):
    session = requests.Session()
    headers = {"Authorization": PARAMS.get('APIAUTH')}
    r = session.get(PARAMS.get('TUTUMURL') + '/api/v1/container/' + uuid + '/logs/', headers=headers)
    r.raise_for_status()
    logs = r.json().get("logs")
    return logs

def call_api(url):
    session = requests.Session()
    headers = {"Authorization": PARAMS.get('APIAUTH')}
    r = session.get(PARAMS.get('TUTUMURL') + url, headers=headers)
    r.raise_for_status()
    container = r.json()
    name = container.get("name").lower()
    uuid = container.get("uuid")
    send = True
    for exclude in PARAMS.get('CONTAINERSTOEXCLUDE'):
        if name.startswith(exclude.lower()):
            send = False
    if send:
        logs = get_logs(uuid)
        print("Send an email")
        monitoring.send_mail_ws(name, uuid, logs)


def on_error(ws, error):
    print error


def on_close(ws):
    print "### closed ###"


def on_message(ws, message):
    msg_as_JSON = json.loads(message)
    type = msg_as_JSON.get("type")

    if type:
        if type == "auth":
            print("Auth completed")
        elif type == "container" and msg_as_JSON.get("action") == "update" and msg_as_JSON.get("state") == "Stopped":
            call_api(msg_as_JSON.get("resource_uri"))


def on_open(ws):
    print "Connected"


def main(parms):
    global PARAMS
    config = monitoring.checkconfig(parms)
    PARAMS = monitoring.loadconfig(config)
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp('wss://stream.tutum.co/v1/events?token={0}&user={1}'.format(PARAMS.get('TOKEN'), PARAMS.get('USERNAME')),
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)

    ws.run_forever()

if __name__ == "__main__":
    main(sys.argv[1:])
