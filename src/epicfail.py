#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4:

# https://github.com/fritzy/SleekXMPP/wiki/XMPP:-The-Definitive-Guide

import sys
import logging
#import time
import urllib
import httplib
from optparse import OptionParser
from datetime import datetime
from datetime import timedelta

import sleekxmpp

import random
import re

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
	reload(sys)
	sys.setdefaultencoding('utf8')
	
CONFERENCE_NAME = u'zadrawch@conference.jabber.ru' #vladivostok@conference.neko.im'	#
NICK_NAME = u'neko~'
PASTEBIN_URL = 'http://pastebin.com/api_public.php'
PASTEBIN_USER = 'neko~'

def my_reply(msg, text):

	#text = text % dict(mucnick=msg.get_mucnick() if len(msg.get_mucnick()) > 0 else u'тебя')

	#if msg.get_type() == 'groupchat' and not text.lower().startswith('/me'):
	#	text = '%s: %s' % (msg.get_mucnick(), text)

	msg.reply(text).send()



def do_help(args, xmpp, msg):
	u"""вывести справку"""

	reply = u'\n' + u'\n'.join([u'%s: %s' % (cmd, fn.__doc__) for cmd, fn in COMMANDS_MASTER.iteritems()])
	reply = reply + u'\n' + u'\n'.join([u'%s: %s' % (cmd, fn.__doc__) for cmd, fn in COMMANDS_EVERYONE.iteritems()]) 
	my_reply(msg, reply)
	

def do_quit(args, xmpp, msg):
	u"""отключиться"""

	xmpp.disconnect()
	import sys
	sys.exit(0)


def do_z(args, xmpp, msg):
	u"""отправить сообщение в конференцию"""

	xmpp.send_message(CONFERENCE_NAME, mbody=args, mtype='groupchat')


def do_rooms(args, xmpp, msg):
	u"""список конференций"""

	rooms = xmpp.muc.getJoinedRooms()
	if not rooms:
		my_reply(msg, u'меня нигде нет')
		return
	
	reply = u'я в ' + u', '.join([u'%s (%s)' % (muc, xmpp.muc.ourNicks[muc]) for muc in rooms])
	my_reply(msg, reply)	


def do_leave(args, xmpp, msg):
	u"""выйти из конференции"""

	# TODO room in args

	if len(msg.get_mucroom()) > 0:
		room = msg.get_mucroom()
		xmpp.muc.leaveMUC(room, xmpp.muc.ourNicks[room], u'злые вы, ухожу я от вас')
	else:
		my_reply(msg, u'x_x')


def do_join(args, xmpp, msg):
	u"""зайти в комнату"""

	# TODO room in args

	conf = CONFERENCE_NAME
	nick = NICK_NAME

	if conf in xmpp.muc.getJoinedRooms():
		my_reply(msg, u'вообще-то я уже там')
	else:
		xmpp.muc.joinMUC(conf, nick)
		
def send_log(args, xmpp, msg):
	u"""получить лог \d - последние сколько-то строк, \dh - последние сколько-то часов. 16 строк например без аргументов или 2h - за последние два часа"""
	n, unit = re.search(ur'^(\d+)(.*)$', args).groups() if len(args) > 0 else (16, '')
	log_file = open(CONFERENCE_NAME + u'-Log.txt', 'r+')
	log_lines = log_file.readlines()
	desired_lines = ''
	log_lines_count = len(log_lines)
	if unit == '':
		for i in range(log_lines_count - int(n) - 1, log_lines_count):
			desired_lines += log_lines[i]
	elif unit == 'h':
		last_line = log_lines[log_lines_count - 1]
		i = log_lines_count - 1
		delta = timedelta(hours=int(n))
		while (datetime.utcnow() - datetime.strptime(re.search(ur'^\[(.*?)\]', last_line).group(1), '%a %b %d %H:%M:%S %Y')) < delta:
			desired_lines = last_line + desired_lines
			i = i - 1
			last_line = log_lines[i]
			while re.search(ur'^\[(.*?)\]', last_line) == None:
				i = i - 1
				last_line = log_lines[i]

	POST = "paste_format=text&paste_code=" + desired_lines + "&paste_name=" + PASTEBIN_USER + "&paste_expire_date=10M&paste_private=1"
	my_reply(msg, u'Отослал блджад, на ' + urllib.urlopen(PASTEBIN_URL, POST).read() + ' тебе.')
	log_file.close()
	
def do_quote(args, xmpp, msg):
	u"""случайная цитата из лога"""
	log_file = open(CONFERENCE_NAME + u'-Log.txt', 'r+')
	log_lines = log_file.readlines()
	m = None
	while not m:
		m = re.search(ur'(^\[.*?\])(.*$)', log_lines[random.randint(0, len(log_lines) - 1)])
	my_reply(msg, m.group(2))
	log_file.close()
	
def do_draw_advice(args, xmpp, msg):
	u"""рисуй"""
	draw_list_file = open('to_draw_list.txt', 'r+')
	draw_lines = draw_list_file.readlines()
	if len(draw_lines) == 0:
		return
	my_reply(msg, u'Рисуй' + draw_lines[random.randint(0, len(draw_lines) - 1)])
	draw_list_file.close()

	
MAX_COMMAND_LEN=12
COMMANDS_MASTER = dict(
	quit=do_quit,
	join=do_join,
	leave=do_leave,
)

COMMANDS_EVERYONE = dict(
	help=do_help,
	z=do_z,
	rooms=do_rooms,
	log=send_log,
	quote=do_quote,
	draw=do_draw_advice
)

def dispatch_command(xmpp, msg):
	#print repr(msg['body']), type(msg['body'])
	l = msg['body'].split(u' ', 1)
	cmd = l[0].lstrip('!').lower()
	if len(cmd) == 0 or len(cmd) > MAX_COMMAND_LEN: return
	args = l[1] if len(l) > 1 else u''

	if COMMANDS_MASTER.has_key(cmd):
		COMMANDS_MASTER[cmd](args, xmpp, msg)
	else:
		if COMMANDS_EVERYONE.has_key(cmd):
			COMMANDS_EVERYONE[cmd](args, xmpp, msg)
		else:
			my_reply(msg, u'не знаю команды %s' % cmd)

def reaction(msg):

	msgtext = unicode(msg['body']).lower()

	if re.match(ur'.*голос.*', msgtext, flags=re.UNICODE) and len(msgtext) <= 32 :
 		my_reply(msg, random.choice([
			u'гав! гав!',
			u'мяу~',
			u'чирик-чирик',
			u'(картошка)',
			u'хрю-хрю',
			u'я тебя люблю :3',
			u'...',
			u'ЗАЕБАЛИ!',
			u'голос'
		]))
		return True
		
	if re.match(ur'гав\b', msgtext, flags=re.UNICODE) and len(msgtext) < 32:
		my_reply(msg, random.choice([
			u'молодец, хорошая собачка!',
			u'/me гладит %(mucnick)s по головке',
			u'фас!'
		]))
		return True 

	return False
	
def has_something_to_draw(msg):
	if (msg == None) or (msg['body'] == ''):
		return False
	match = re.search(u'([рР][иИ][сС][уУоО][вВюЮеЕйЙ][аАшШ]?[тТлЛьЬ]?[ьЬ]?)(.*)', unicode(msg['body']))
	if match:
		to_draw_list_file = open('to_draw_list.txt', 'a+')
		to_draw_list_file.write(match.group(2) + u'\n')
		to_draw_list_file.close()
		return True
	return False

class EchoBot(sleekxmpp.ClientXMPP):

	def __init__(self, jid, password):

		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.add_event_handler("session_start", self.start)
		self.add_event_handler("message", self.message)
		self.add_event_handler("roster_update", self.show_roster)

	
	def start(self, event):

		self.getRoster()
		self.sendPresence()

		# muc start
		self.muc = self.plugin['xep_0045']
		#self.muc.joinMUC('zadrawch@conference.jabber.ru', 'baka_neko_bot', wait=False)
		#conf = muc.getRoomConfig('zadrawch@conference.jabber.ru')
		#print 'conf: ', conf, '\n'


	def message(self, msg):

		msgtext = unicode(msg['body']).lower()
		from_text_parsed = unicode(msg['from']).replace('zadrawch@conference.jabber.ru/', '')
		log_file = open(CONFERENCE_NAME + u'-Log.txt', 'a+')
		log_file.write('[' + datetime.utcnow().ctime() + '] ' + from_text_parsed + ': ' + unicode(msg['body']) + '\n')
		log_file.close()
	
		if msg.get_type() == 'groupchat':

			if msg.get_mucnick() == 'neko~': return # ignore own messages! TODO hardcoded

			if reaction(msg): return
			
			if has_something_to_draw(msg): return
			
			# warning: mokey code below
			if (msg.get_mucnick().startswith('ktt7') or msg.get_mucnick().startswith('ktt4') or msg.get_mucnick().startswith('ktt6')) and msgtext.startswith('!'):
				dispatch_command(self, msg)
			else:
				if COMMANDS_EVERYONE.has_key(msg['body'].split(u' ', 1)[0].lstrip('!').lower()):
					dispatch_command(self, msg)
				
		else: # private
	
			if unicode(msg['from']).startswith('baka_neko_bot@'): return # TODO hardcoded!
	
			if unicode(msg['from']).startswith('mapholameth') and msgtext.startswith('!'):
				dispatch_command(self, msg)


	def show_roster(self, event):

		self.saved_roster = event



def cmdloop():

	global xmpp
	
	while True:
		print ">"
		command_input = raw_input()

		if command_input == 'quit':
			xmpp.disconnect()
			import sys
			sys.exit(0)
			
		xmpp.send_message(CONFERENCE_NAME, mbody=unicode(command_input), mtype='groupchat')





if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")

    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = EchoBot(opts.jid, opts.password)
    xmpp.registerPlugin('xep_0030') # Service Discovery
    xmpp.registerPlugin('xep_0004') # Data Forms
    xmpp.registerPlugin('xep_0060') # PubSub
    xmpp.registerPlugin('xep_0199') # XMPP Ping
    xmpp.registerPlugin('xep_0045')

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        # If you do not have the pydns library installed, you will need
        # to manually specify the name of the server if it does not match
        # the one in the JID. For example, to use Google Talk you would
        # need to use:
        #
        # if xmpp.connect(('talk.google.com', 5222)):
        #     ...
        xmpp.process(threaded=True)
        print("Done")
    else:
        print("Unable to connect.")

    cmdloop()

