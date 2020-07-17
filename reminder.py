import asyncio
import dateparser
import datetime
import math
import logging
import isodatetime.parsers as dtparse
import isodatetime.data as dtdata
from botdb import BotDB

log = logging.getLogger('LongSphinx.Reminder')

DBNAME = 'schedule'
DBKEY = '0'
window = datetime.timedelta(minutes=5)

def load_reminders():
	with BotDB(DBNAME, botName) as db:
		if DBKEY in db:
			return db[DBKEY]
		else:
			return []

def save_reminders(schedule):
	with BotDB(DBNAME, botName) as db:
		db[DBKEY] = schedule

def save_one_reminder(channel, when_time, msg):
	schedule = load_reminders()
	schedule.append((channel, when_time, msg))
	save_reminders(schedule)

def delete_reminder(reminder):
	schedule = load_reminders()
	schedule.remove(reminder)
	save_reminders(schedule)

async def set_all_saved_reminders(client, botNameParam):
	global botName
	botName = botNameParam
	for reminder in load_reminders():
		if reminder[1] > datetime.datetime.utcnow():
			await set_reminder(reminder[1], client, reminder[0], reminder[2])
		else:
			delete_reminder(reminder)

async def send_message(client, channel, msg, time):
	if (time - window) <= datetime.datetime.utcnow() <= (time + window): #extra check to avoid random mistimed messages
		await client.send_message(channel, msg)
	else:
		log.error('Mistimed reminder.')

def parse_argstring(argstring):
	splitindex = max(argstring.rfind(' in '), argstring.rfind(' at '))
	when_time = dateparser.parse(argstring[splitindex:], settings={'TIMEZONE': 'UTC'})
	if when_time.tzinfo is not None:
		when_time = when_time.replace(tzinfo=None)
	msg = 'Reminder: {0}'.format(argstring[:splitindex])
	displaytext = argstring[splitindex:]
	return when_time, msg, displaytext

async def list_my_reminders(user, **kwargs):
	all_reminders = load_reminders()
	all_reminders.sort(key= lambda x: x[1])
	reminders = [f'{friendly_until_string(when)}: {msg.replace("Reminder: ", "")}' for (channel, when, msg) in all_reminders if channel == user]
	return '\n'.join(reminders)

async def message_reminder(argstring, client, user, **kwargs):
	when_time, msg, displaytext = parse_argstring(argstring)
	save_one_reminder(user, when_time, msg)
	await set_reminder(when_time, client, user, msg)
	return 'I\'ll send you a reminder in {0}.'.format(friendly_until_string(when_time))

async def set_reminder(when_time, client, channel, msg):
	if when_time > datetime.datetime.utcnow():
		delay = when_time.timestamp() - datetime.datetime.utcnow().timestamp()
		loop = asyncio.get_event_loop()
		loop.call_later(delay, lambda: loop.create_task(send_message(client, channel, msg, when_time)))
	else:
		log.warning('Ignoring scheduled event in the past: ' + str(when_time))

def friendly_until_string(when):
	# This is dense as fuck, I know. Starting from the inside:
	# Subtract now from when to get a duration
	# Convert duration to string, it looks like `10 days, 4:55:21.2435`
	# Split at the '.' and take the first part, to strip off the partial seconds
	# Split on ':' then unpack that list into the arguments for format, resulting in `10 days, 4h, 55m, 21s`
	# Replace ' days' with 'd' to get `10d, 4h, 55m, 21s`
	# Now as long as I always remember to keep this comment up to date - hahahahahaha
	return '{0}h, {1}m, {2}s'.format(*str(when-datetime.datetime.utcnow()).split('.')[0].split(':')).replace(' days', 'd')

def get_first_after(recurrence, timepoint):
    """Returns the first valid scheduled recurrence after the given timepoint, or None."""
    if timepoint is None:
        return None
    if recurrence.start_point is not None:
        iterations, seconds_since = dividemod(timepoint - recurrence.start_point, recurrence.duration)
        log.error('iterations: ' + str(iterations) + ' and seconds: ' + str(seconds_since))
        if not recurrence.repetitions or recurrence.repetitions > iterations:
        	return timepoint + (recurrence.duration - dtdata.Duration(seconds=math.floor(seconds_since)))
    '''else: # going in reverse
        candidate = None
        for next_timepoint in recurrence:
            if next_timepoint < timepoint:
                return candidate
            candidate = next_timepoint
        # when loop is done, this is the first overall timepoint (chronologically)
        return candidate'''

def dividemod(duration, divisor):
	return divmod(duration.get_seconds(), divisor.get_seconds())

async def set_recurring_message(recur_string, client, channel, msg):
	recurrence = dtparse.TimeRecurrenceParser().parse(recur_string)
	now = dtdata.get_timepoint_for_now()
	when_time = get_first_after(recurrence, now)
	if when_time is not None:
		delay = float(when_time.get("seconds_since_unix_epoch")) - datetime.datetime.now().timestamp()
		loop = asyncio.get_event_loop()
		loop.call_later(delay, lambda: loop.create_task(send_recurring_message(recur_string, client, channel, msg)))

async def send_recurring_message(recur_string, client, channel, msg):
	await client.send_message(channel, msg)
	await set_recurring_message(recur_string, client, channel, msg)

def readme(**kwargs):
	return '''
* `!remind <message> in <duration>`: Sends a reminder PM to the requester. 
> Example: `!remind laundry in 30 minutes`
* `!remind <message> at <time>`: Same as above, but sends at the time specified in UTC. Remember to specify AM or PM or use 24-hour clock.
* `!reminders`: Shows all of your set reminders, and how long until they occur.'''
