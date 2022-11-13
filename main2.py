from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from datetime import datetime
from asyncio import get_event_loop, Future, ensure_future
import random
from time import sleep
from threading import Thread

if TYPE_CHECKING:
    from receiver import User


@dataclass
class Habit:
    id: int
    name: str
    interval: Optional[int] = None


def _call_later(seconds: float, func: Callable, *args, **kwargs):
    sleep(seconds)
    func(*args, **kwargs)


def call_later(seconds: float, func: Callable, *args, **kwargs):
    # get_event_loop().call_later(seconds, ensure_future, func(*args, **kwargs))
    Thread(target=_call_later, args=[
           seconds, func, * args], kwargs=kwargs).start()


def peck_once(user: User, habit: Habit):
    user.send(f"Reminder: {habit.name}")


def peck_multiple(user: User, habit: Habit):
    peck_once(user, habit)
    call_later(habit.interval, peck_multiple, user, habit)


def woodpecker(user: User):
    name = yield "What is your name?"
    habits = [Habit]
    user_id = random.randrange(100000)
    # call_later(10, peck, user, habit)

    while True:
        msg = yield

        if msg == 'help':
            # TODO
            user.send(
                "what can i do for you? if you text 'add', we can add a new habit for you! Say 'delete' if you want to delete one of your habits!")
        elif msg == 'add':
            new_habit = yield "what habit would you like to add?"
            if new_habit in habits:
                user.send(
                    "looks like i already have that habit stored. to check which habits you have stored so far, text me 'habits'!")
            reminder_type = yield "how would you like to receive reminders? text me 'one-time' or 'recurring'."

            if reminder_type == 'one-time':
                time_str = yield "in how many seconds should i remind you?"
                time = int(time_str)
                habit = Habit(user_id, new_habit)
                habits.append(habit)
                user.send("okee, i'll remind you in " + time + " seconds!")
                call_later(time, peck_once, user, habit)

            elif reminder_type == 'recurring':
                interval_str = yield "how long should we wait between each reminder (in seconds)?"
                interval = int(interval_str)
                habit = Habit(user_id, new_habit, interval)
                habits.append(habit)
                call_later(interval, peck_multiple, user, habit)
                user.send(
                    f"okee, i'll remind you every {interval} seconds, starting in {interval} seconds from now!")
            else:
                user.send(
                    "that's not a reminder type, silly! if you still want to add something type 'add' again!")
        elif msg == 'habits':
            user.send("here are your habits:")
            for habit in habits:
                habList = ''
                for habit in habits:
                    habList += "habit: " + habit.name + " | interval: " + habit.interval + "\n"
                user.send(habList)
        elif msg == 'delete':
            user.send("here are your current habits:")
            for habit in habits:
                habList = ''
                for habit in habits:
                    habList += "habit: " + habit.name + " | interval: " + habit.interval + "\n"
                user.send(habList)
            habit_todelete = yield "which habit would you like to delete?"
            for habit in habits:
                if habit.name == habit_todelete:
                    habits.remove(habit)
                    user.send("i deleted " + habit.name + " !")
                else:
                    user.send(
                        "hmm... it seems like that's not one of your habits. text 'delete' to remove a habit!")
            user.send("not yet implemented.")
        elif msg == 'update':
            user.send("not yet implemented.")  # TODO
        else:
            user.send("unknown command :( try again!")
