from datetime import datetime
import logging
from botdb import BotDB

dbname = "notices"
log = logging.getLogger('LongSphinx.Notice')
botName = "unknown"

# replace all unused parameters with "**kwargs"
async def notices(
		user, # Author of the message that invoked the command
		server, # Server in which command was invoked
		argstring, # Everything after the first space. Inputs/parameters for the command.
		botname, # Name of the active bot, e.g. 'dev' or 'tim'
		**kwargs
	):
	botName = botname
	subcommand = ''
	if argstring:
		subcommand = argstring.split()[0]
	if subcommand == 'list':
		return listNotices(server)
	if subcommand == 'add':
		return addNotice(user, server, argstring.split()[1], argstring[argstring.find(' ', argstring.find(' ') + 1)+1:])
	if subcommand == 'delete':
		return deleteNotice(user, server, argstring.split()[1])
	return readNotice(server, subcommand)

# Most of these are probably useless for a readme, but you never know
def readme(
		**kwargs
	):
	return '''View and manage server notices.
 * `!notice` view the latest notice.
 * `!notice list` list all notice titles.
 * `!notice <title>` view a specific notice.
And for those with admin permissions:
 * `!notice add <title> <text>` add a notice, or replace an existing one.
 * `!notice delete <title>` delete a notice.
'''

def addNotice(user, server, title, text):
	if (user.guild_permissions.administrator):
		notices = loadNotices(server.id)
		newNotice = {'text': text, 'created': datetime.utcnow().isoformat()}
		reply = f'Updated notice "{title}":\n'
		if title in notices:
			reply += f'Old content:\n```\n{notices[title]["text"]}\n```\n'
			newNotice['created'] = notices[title]['created']
		reply += f'New content:\n>>> {text}'
		notices[title] = newNotice
		saveNotices(notices, server.id)
		return reply
	return "Only a server admin can add notices."

def deleteNotice(user, server, title):
	if (user.guild_permissions.administrator):
		notices = loadNotices(server.id)
		if title in notices:
			reply = f'Deleted notice {title}, former content was:\n```\n{notices[title]["text"]}\n```'
			del notices[title]
			saveNotices(notices, server.id)
			return reply
		return f'Notice "{title}" not found.'
	return "Only a server admin can delete notices."

def listNotices(server):
	return 'Notices on this server:\n' + '\n'.join(loadNotices(server.id).keys())

def readNotice(server, title):
	notices = loadNotices(server.id)
	if not title:
		return '>>> ' + getLatest(notices)
	if title in notices:
		return '>>> ' + notices[title]['text']
	return f'Notice "{title}" not found.'

def loadNotices(serverId):
	with BotDB(dbname, botName) as db:
		if str(serverId) not in db:
			db[str(serverId)] = {}
		notices = db[str(serverId)]
	return notices

def saveNotices(notices, serverId):
	with BotDB(dbname, botName) as db:
		db[str(serverId)] = notices

def getLatest(notices):
	try:
		return sorted(notices.values(), key=lambda notice: notice['created'])[-1]['text']
	except:
		return "No notices found on this server."