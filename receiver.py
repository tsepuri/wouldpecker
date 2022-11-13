from __future__ import annotations
from typing import *
import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import namedtuple
from asyncio import get_event_loop, Future, ensure_future, new_event_loop, set_event_loop
from twilio.rest import Client
from enum import Enum
import openai
from flask import Flask, request, redirect
from main2 import woodpecker
from time import sleep
from threading import Thread


def _call_later(seconds: float, func: Callable, *args, **kwargs):
    sleep(seconds)
    func(*args, **kwargs)


def call_later(seconds: float, func: Callable, *args, **kwargs):
    # get_event_loop().call_later(seconds, ensure_future, func(*args, **kwargs))
    Thread(target=_call_later, args=[
           seconds, func, * args], kwargs=kwargs).start()


# def woodpecker(user: User):
#     body = yield
#     print(f"New woodpecker: {user.number}: {body}")

#     user.send('Hello Woodpecker!')

#     while True:
#         response = yield
#         print(f"Got response: {user.number}: {response}")
#         user.send(f"You said: '{response}'")


# TODO: move to environment variables
with open('creds.json', 'r') as f:
    creds = json.load(f)

    def get_cred(name: str) -> str:
        value = creds.get(name.lower(), '').strip()
        if value == '' or value is None:
            raise ValueError(f"Missing credential: {name}")
        return value

    TWILIO_ACCOUNT_SID = get_cred('twilio_account_sid')
    TWILIO_AUTH_TOKEN = get_cred('twilio_auth_token')
    FROM_NUMBER = get_cred('twilio_from_number')
    openai.api_key = get_cred('open_ai_api_key')


app = Flask(__name__)
loop = get_event_loop()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def response(prompt): return openai.Completion.create(
    engine="text-davinci-002",
    prompt=prompt,
    temperature=0.7,
    max_tokens=150,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
)


stub_messages = []


####################################################################################################
# Users
####################################################################################################

_USER_MAP = {}


class GeneratorEntry(NamedTuple):
    generator: Generator[Optional[str], str, None]
    expires_at: Optional[datetime]
    autocancel: bool


class GeneratorExpiration(Exception):
    """ Throw into a generator when it expires. """


class GeneratorAutocancellation(GeneratorExpiration):
    """ Thrown into a generator when a autocancel=True. """


@dataclass
class User:
    @classmethod
    def get(cls, number: str) -> User:
        if number not in _USER_MAP:
            _USER_MAP[number] = cls(number)
        return _USER_MAP[number]

    def __post_init__(self):
        assert self.number not in _USER_MAP, "duplicate user!"
        print(f"Created user: {self.number}")
        _USER_MAP[self.number] = self
        self.push_generator(woodpecker(
            self), expires_at=None, autocancel=False)

    number: str

    generators: List[GeneratorEntry] = field(init=False, default_factory=list)

    def push_generator(self, generator: Generator[Optional[str], str, None], expires_at: Optional[datetime] = None, autocancel: bool = True):
        # for entry in self.generators:
        #     if entry.autocancel:
        #         try:
        #             entry.generator.throw(GeneratorAutocancellation())
        #         except GeneratorAutocancellation:
        #             pass
        #         self.generators.remove(entry)

        self.generators.append(GeneratorEntry(
            generator=generator,
            expires_at=expires_at,
            autocancel=autocancel
        ))

        self.step(None)  # must do this to initialize generator

    def schedule_generator(self, seconds: float, generator: Generator[Optional[str], str, None], expires_at: Optional[datetime] = None, expires_in: Optional[float] = None, autocancel: bool = True):
        # assert expires_at is None or expires_in is None, "can't have expires at and expires in"
        # if expires_in is not None:
        #     expires_at = datetime.now() + timedelta(seconds=expires_in)
        call_later(seconds, self.push_generator, generator=generator,
                   expires_at=expires_at, autocancel=autocancel)

    @property
    def is_stub(self) -> bool:
        return self.number == 'stub'

    def send(self, text: str) -> None:
        if self.is_stub:
            stub_messages.append("Woodpecker: " + text)
            return

        twilio_client.messages.create(
            to=self.number,
            body=text,
            from_=FROM_NUMBER,
        )

    def step(self, text: str):
        # while self.generators[-1].expires_at is not None and self.generators[-1].expires_at <= datetime.now():
        #     try:
        #         self.generators[-1].generator.throw(GeneratorExpiration())
        #     except GeneratorExpiration:
        #         pass
        #     self.generators.pop()

        if len(self.generators) == 0:
            print(f"{self.number}: No generators!")
            self.send('Error! Please restart.')
            _USER_MAP[self.number] = None
            return

        try:
            msg = self.generators[-1].generator.send(text)
        except StopIteration:
            if len(self.generators) >= 2:
                print(
                    f"Generator {self.generators[-1]} exited for: {self.number}, this is OK because we have multiple on the stack.")
                self.generators.pop()
                return

            print(
                f"Generator {self.generators[-1]} exited for: {self.number}, but the stack is now empty!")
            self.send('Error! Please restart.')
            _USER_MAP[self.number] = None
            return

        if msg is not None:
            self.send(msg)

####################################################################################################
# Flask
####################################################################################################


@app.route('/messages', methods=['GET'])
def get_messages():
    return '\n\n'.join(stub_messages)


@app.route('/', methods=['GET'])
def home():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Woodpecker</title>
</head>
<body>
    <h1>Woodpecker</h1>
    <pre disabled style="width: 95vw; height: 80vh; overflow-x: wrap; overflow-y: scroll; border: 1px solid black; padding: 5px;" id="messages">
    {get_messages}
    </pre>
    <form action="/send-message" method="POST">
        <input type="text" id="text" name="text" placeholder="Talk to Woodpecker" style="width: 80vw"/>
        <input type="submit" value="Send"/>
    </form>
    <script type="text/javascript">
    setInterval(() => fetch('/messages').then(res => res.text()).then((msgs) => document.getElementById('messages').innerText = msgs), 1);
    document.getElementById('text').focus();
    </script>
</body>
"""


@app.route('/send-message', methods=['POST'])
def send_message():
    text = request.values.get('text', None)
    if text is None:
        return 'Must have text!', 400

    stub_messages.append("You: " + text)

    user = User.get('stub')
    if len(text.split()) <= 2:
        user.step([text.lower()])
    else:
        keywords = response(f"Extract keywords from this text:\n{text}")
        keywords = keywords.choices[0].text
        if "\n" in keywords:
            keywords = (keywords[keywords.rindex("\n")+1:]).split(',')
            keywords = [keyword.lower() for keyword in keywords]
        if "add" in text.lower():
            keywords.append("add")
        user.step(keywords)

    return redirect('/')


@app.route("/sms", methods=['GET', 'POST'])
def on_sms():
    """Respond to incoming calls with a simple text message."""
    number = request.values.get('From', None)
    body = request.values.get('Body', None)

    print(f"Got Message: {number}: {body}")

    if number is None or body is None:
        print("ERROR: Missing number or body!")
        return ''

    user = User.get(number)
    text = body
    if len(text.split()) <= 2:
        user.step([text.lower()])
    else:
        keywords = response(f"Extract keywords from this text:\n{text}")
        keywords = keywords.choices[0].text
        if "\n" in keywords:
            keywords = (keywords[keywords.rindex("\n")+1:]).split(',')
            keywords = [keyword.lower() for keyword in keywords]
        if "add" in text.lower():
            keywords.append("add")
        user.step(keywords)

    return ''


if __name__ == '__main__':
    app.run(debug=True)
