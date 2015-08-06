#!python
import ConfigParser
import sys
import getopt
import mandrill
from threading import Thread
import pprint
import ws
import who_is_not_online

TOKEN = ""
USERNAME = ""
APIAUTH = "Apikey " + USERNAME + ":" + TOKEN
TUTUMURL = "https://dashboard.tutum.co"
CONTAINERLINK = TUTUMURL + "/container/show/"
CONTAINERSTOEXCLUDE = []
MANDRILL_CLIENT = mandrill.Mandrill('')
EMAILS = []
MANUAL_URL = []
CONFIGPATH = ""
CONF = ConfigParser.ConfigParser()

def send_mail_ws(name, uuid):
    message = {
        'from_email': 'monitor@webtales.fr',
        'from_name': 'Monitoring Rubedo',
        'html': "<h1>Monitoring</h1><p>The container <strong><a href='" + CONTAINERLINK + uuid + "/#container-logs' >" + name + "</a></strong> went down !</p>",
        'subject': 'Monitoring Detection for ' + name,
        'to': EMAILS
    }
    result = MANDRILL_CLIENT.messages.send(message=message, async=False)
    pprint.pprint(result)

def send_mail_vhost(vhosts):
    if len(vhosts) == 1:
        message = {
            'from_email': 'monitor@webtales.fr',
            'from_name': 'Monitoring Rubedo',
            'html': "<h1>Monitoring</h1><p>The website <strong><a href='" + "http://" + vhosts[0] + "' >" + vhosts[0] + "</a></strong> is not responding !</p>",
            'subject': 'Monitoring Detection for ' + vhosts[0],
            'to': EMAILS
        }
    else:
        body = "<h1>Monitoring</h1>"
        for vhost in vhosts:
            body = body + "<p>The website <strong><a href='" + "http://" + vhost + "' >" + vhost + "</a></strong> is not responding !</p>"
        message = {
            'from_email': 'monitor@webtales.fr',
            'from_name': 'Monitoring Rubedo',
            'html': body,
            'subject': 'Monitoring Detection for multiple websites',
            'to': EMAILS
        }
    result = MANDRILL_CLIENT.messages.send(message=message, async=False)
    pprint.pprint(result)

def checkconfig(argv):
    global CONFIGPATH
    configgiven = False
    try:
        opts, args = getopt.getopt(argv, "hc:", ["help", "config"])
    except getopt.GetoptError:
        print ('monitoring.py -c ABSOLUTE_PATH_TO_CONFIG_FILE\n'
               'monitoring.py --config ABSOLUTE_PATH_TO_CONFIG_FILE')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print ('monitoring.py -c ABSOLUTE_PATH_TO_CONFIG_FILE\n'
                   'monitoring.py --config ABSOLUTE_PATH_TO_CONFIG_FILE')
            sys.exit()
        elif opt in ("-c", "--config"):
            if arg.startswith("/"):
                print(arg)
                CONFIGPATH = arg
                CONF.read(arg)
                configgiven = True
            else:
                print('Absolute path is required')
                sys.exit(2)
    if not configgiven:
        print('Config file missing.\n'
              'monitoring.py -c ABSOLUTE_PATH_TO_CONFIG_FILE\n'
              'monitoring.py --config ABSOLUTE_PATH_TO_CONFIG_FILE')
        sys.exit(2)
    return CONF


def loadconfig(config):
    global TOKEN, USERNAME, APIAUTH, TUTUMURL, CONTAINERLINK, CONTAINERSTOEXCLUDE,MANDRILL_CLIENT, MANUAL_URL, EMAILS
    EMAILS = []
    try:
        mandrilltoken = config.get("Mandrill", "apikey")
        MANDRILL_CLIENT = mandrill.Mandrill(mandrilltoken)
    except ConfigParser.Error:
        print('Config file does not have a Mandrill section with an apikey')
        sys.exit(2)
    try:
        TOKEN = config.get("Tutum", "token")
        USERNAME = config.get("Tutum", "username")
        APIAUTH = "Apikey " + USERNAME + ":" + TOKEN
        TUTUMURL = "https://dashboard.tutum.co"
        CONTAINERLINK = TUTUMURL + "/container/show/"
    except ConfigParser.Error:
        print('Config file does not have a Tutum section with a token and a username')
        sys.exit(2)
    try:
        mails = config.options("Mails")
        if len(mails) < 1:
            print('Config file does not have a Mails section with atleast one mail')
            sys.exit(2)
        for mail in mails:
            EMAILS.append({'email': mail, 'name': config.get("Mails", mail)})
    except ConfigParser.Error:
        print('Config file does not have a Mails section with atleast one mail')
        sys.exit(2)
    try:
        CONTAINERSTOEXCLUDE = config.options("Exclude")
    except ConfigParser.Error:
        print('No exclude containers')
    try:
        MANUAL_URL = config.options("Manual_Url")
    except ConfigParser.Error:
        print('No manuals url')
    return {
        'TOKEN': TOKEN,
        'USERNAME': USERNAME,
        'APIAUTH': APIAUTH,
        'TUTUMURL': TUTUMURL,
        'CONTAINERLINK': CONTAINERLINK,
        'CONTAINERSTOEXCLUDE': CONTAINERSTOEXCLUDE,
        'MANDRILL_CLIENT': MANDRILL_CLIENT,
        'EMAILS': EMAILS,
        'MANUAL_URL': MANUAL_URL
    }


if __name__ == "__main__":
    Config = checkconfig(sys.argv[1:])
    loadconfig(Config)
    website = Thread(target=who_is_not_online.main, args=(sys.argv[1:],))
    tutum = Thread(target=ws.main, args=(sys.argv[1:],))
    tutum.start()
    website.start()
    # os.system("python who_is_not_not_online.py -c " + CONFIGPATH)
