from __future__ import annotations
from typing import *
import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from asyncio import get_event_loop, Future, ensure_future, new_event_loop, set_event_loop
from twilio.rest import Client
from enum import Enum
from flask import Flask, request, redirect
from main2 import woodpecker

NO_TWILIO = os.environ.get('NO_TWILIO', '0') == '1'


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


app = Flask(__name__)
loop = get_event_loop()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
stub_messages = []


####################################################################################################
# Users
####################################################################################################

_USER_MAP = {}


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
        self.generator = woodpecker(self)
        self.step(None)  # must to this to setup generator

    number: str

    generator: Generator[Optional[str], str, None] = field(init=False)

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
        try:
            msg = self.generator.send(text)
        except StopIteration:
            print(f"Generator exited for: {self.number}!")
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
    user.step(text)

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

    user.step(body)

    return ''


if __name__ == '__main__':
    app.run(debug=False)
