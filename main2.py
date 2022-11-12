from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from datetime import datetime
from asyncio import get_event_loop, Future, ensure_future
from twilio.rest import Client

loop = get_event_loop()
users: Dict[str, User] = {}


@dataclass
class User:
	number: str

	pending_input: Optional[Future] = None

	async def send(self, text: str) -> None:
		twilio.send_sms(self.number, text)

	async def input(self) -> str:
		self.pending_input = loop.create_future()
		return await self.pending_input

	async def prompt(self, text: str) -> str:
		self.send(text)
		return await self.input()

# Switchable
@dataclass
class Habit:
	id: int
	name: str
	interval: int

def call_later(seconds: float, func: Callable, *args, **kwargs):
	return loop.call_later(seconds, ensure_future, func(*args, **kwargs))

async def peck(user: User, habit: Habit):
	pass

async def woodpecker(user: User, body: str):
	name = await user.prompt("What is your name?")
	habits = [Habit]

	call_later(10, peck, user, habit)

	while True:
		msg = await user.input()

		if msg == 'help':
			await user.send("What can I do for you? ") # TODO
		elif msg == 'add':
			habit_toadd = await user.prompt("What would you like me to remind you to do?")
			reminder_type = await user.prompt("How would you like to receive reminders? Type 'one-time' or 'reccuring")
		if reminder_type == 'one-time':
					
				elif reminder_type == 'reccuring':

				else:
					user.send("That's not a reminder type! ")
					user.prompt("What would you like me to remind you to do?")
		elif msg == 'habits':
			await user.send()
		elif msg == 'delete':
			await user.send("Not yet implemented.")
		elif msg == 'update':
			await user.send("Not yet implemented.") # TODO
		else:
			await user.send("Unknown command!")
		
		  
	
	