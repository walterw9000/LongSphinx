import re

async def autoreact(message, conf, **kwargs):
	for emoji in conf.get_object(message.guild, 'autoreact'):
		for trigger in emoji['triggers']:
			if re.search(trigger, message.content, re.IGNORECASE):
				await message.add_reaction(emoji['emoji'])