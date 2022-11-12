# Twilio: https://www.twilio.com/docs/sms/tutorials/how-to-send-sms-messages-python
# Cohere: 
# Database: htt

# Download the helper library from https://www.twilio.com/docs/python/install
from __future__ import annotations
import os
from typing import *
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
from twilio.rest import Client

@dataclass
class User:
	number: str
	name: str
	pending_event: Event
	habits: List[Habit] = field(default_factory=list)


# Switchable
@dataclass
class Habit:
	user: User
	id: int
	name: str
	interval: int


class Handlers:
	@staticmethod
	def test_ping(w: Woodpecker, event: Event):
		w.respond(event, 'Hello World!')

	@staticmethod
	def signup(w: Woodpecker, event: Event):
		w.respond(event, "Welcome, I'm Welly the woodpecker! I am here to help you spread your wings and fly. I'll do this by pecking at you (gently) with reminders. Let me meet you! What's your first name?")
		event.user.pending_event = Event(EventType.SET_NAME, event.user, None, {})
	
	@staticmethod
	def set_name(w: Woodpecker, event: Event):
		pass
		
	@staticmethod
	def list_habits(w: Woodpecker, event: Event): ...

	@staticmethod
	def create_habit(w: Woodpecker, event: Event): ...

	@staticmethod
	def peck_habit(w: Woodpecker, event: Event): ...

class EventType(Enum):
	TEST_PING = Handlers.test_ping

	SIGNUP = Handlers.signup
	LIST_HABITS = Handlers.list_habits

	CREATE_HABIT = Handlers.create_habit
	# DELETE_HABIT = 'DELETE_HABIT'
	# UPDATE_HABIT = 'UPDATE_HABIT'

	PECK_HABIT = Handlers.peck_habit

@dataclass
class Event:
	type: EventType
	user: User
	habit: Optional[Habit]
	data: dict = field(default_factory=dict)



class TwilioManager:
	# Find your Account SID and Auth Token at twilio.com/console
	# and set the environment variables. See http://twil.io/secure
	TWILIO_ACCOUNT_SID = "AC7a632b4c9ce024b6428187f6b5fa2e5d" # TODO: Move to ENV VAR:  os.environ['TWILIO_TWILIO_ACCOUNT_SID']
	TWILIO_AUTH_TOKEN = "9cca78cfa1c970d4eda89ea197cc1015" # TODO: Move to ENV VAR: os.environ['TWILIO_TWILIO_AUTH_TOKEN']
	FROM_NUMBER = "+19135134160"

	client: Client

	def __init__(self):
		self.client = Client(self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN)

	def send_sms(self, to: str, body: str) -> None:
		message = self.client.messages \
			.create(
				to=to,
				body=body,
				from_=self.FROM_NUMBER,
				# media_url=['https://c1.staticflickr.com/3/2899/14341091933_1e92e62d12_b.jpg']
			)

	def on_sms_received(self, number: str, body: str) -> None: raise NotImplemented
	def parse_sms(self, from_number: str, body: str) -> None: raise NotImplemented


class Woodpecker:
	# handlers: Dict[EventType, Callable[[EventManager, Event], None]]

	twilio: TwilioManager
	
	def __init__(self):
		self.twilio = TwilioManager()

	def run(self, event: Event) -> None:
		event.type(self, event)
		
	def respond(self, event: Event, body: str) -> None:
		self.twilio.send_sms(event.user.name, body)

time_triggers: List[Tuple[datetime, Event]] = []

async def check_timers():
	while True:
		for entry in time_triggers:
			time, event = entry
			if time <= datetime.now():
				time_triggers.remove(entry)
				Woodpecker.run(event)
		await asyncio.sleep(1)

if __name__ == '__main__':
	Woodpecker().run(Event(EventType.TEST_PING, None, None, None))


# Example