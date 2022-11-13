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
    stopped: bool = False
    destroyed: bool = False


def _call_later(seconds: float, func: Callable, *args, **kwargs):
    sleep(seconds)
    func(*args, **kwargs)


def call_later(seconds: float, func: Callable, *args, **kwargs):
    # get_event_loop().call_later(seconds, ensure_future, func(*args, **kwargs))
    Thread(target=_call_later, args=[
           seconds, func, * args], kwargs=kwargs).start()


def peck_once(user: User, habit: Habit):
    if habit.destroyed or habit.stopped:
        return
    finished = (yield f"Have you done your {habit.name} yet?").lower()
    if 'yes' in finished or 'yeah' in finished:
        user.send("Great! Ending habit.")
        habit.destroyed = True
    elif 'no' in finished or 'nope' in finished:
        user.send("You got this!")
    elif 'pause' in finished:
        user.send(
            f"Maybe next time!")
        habit.stopped = True


def peck_multiple(user: User, habit: Habit):
    user.schedule_generator(habit.interval, peck_multiple(
        user, habit), expires_in=habit.interval, autocancel=True)
    yield from peck_once(user, habit)
    if habit.destroyed or habit.stopped:
        return


def habit_to_string(habits, only_stopped=False):
    habList = "Here are your habits:\n"
    for habit in habits:
        if not habit.destroyed and not (only_stopped and not habit.stopped):
            habList += f"habit: {habit.name} | interval: {str(habit.interval)} seconds | ongoing: {str(not habit.stopped)} \n"
    return habList


def woodpecker(user: User):
    yield "Hi! Welcome to Wouldpecker!"
    user.send("Say goodbye to procrastination with Wouldpecker, the habit tracker that keeps pecking at you until you until you soar to new heights!")
    name = yield "What is your name?"
    user.send(
        f"Hi {name}! What can i do for you? If you text 'add' we can add a new habit for you!")
    habits = []
    user_id = random.randrange(100000)
    # call_later(10, peck, user, habit)

    while True:
        msg = yield
        if 'help' in msg:
            user.send(
                "what can i do for you? if you text 'add', we can add a new habit for you! Say 'delete' if you want to delete one of your habits! Say 'habits' if you want to list your habits!")
        elif 'add' in msg:
            new_habit = ""
            if len(msg.split(' ')) > 1:
                for string in msg.split(' '):
                    if string != "habit" and string != "hobby" and string != "add" and len(new_habit) == 0:
                        new_habit = string
                        break
            if len(new_habit) == 0:
                new_habit = yield "what habit would you like to add?"
                # if new_habit in habits:
                #     user.send(
                #         "looks like i already have that habit stored. to check which habits you have stored so far, text me 'habits'!")
            reminder_type = yield "how would you like to receive reminders? text me 'one-time' or 'recurring'."

            if 'one-time' in reminder_type:
                time_str = yield "in how many seconds should i remind you?"
                time = int(time_str.strip())
                habit = Habit(user_id, new_habit)
                habits.append(habit)
                user.send(f"okee, i'll remind you in {time} seconds!")
                user.schedule_generator(time, peck_once(
                    user, habit), expires_in=time, autocancel=True)

            elif 'recurring' in reminder_type:
                interval_str = yield "how long should we wait between each reminder (in seconds)?"
                interval = int(interval_str.strip())
                habit = Habit(user_id, new_habit, interval)
                habits.append(habit)
                user.schedule_generator(habit.interval, peck_multiple(
                    user, habit), expires_in=habit.interval, autocancel=True)
                user.send(
                    f"okee, i'll remind you every {interval} seconds, starting in {interval} seconds from now!")
            else:
                user.send(
                    "that's not a reminder type, silly! if you still want to add something type 'add' again!")
        elif 'start' in msg:
            habit_text = habit_to_string(habits, True)
            habit_tostart = yield f"{habit_text}\nWhich habit would you like to start?"
            for habit in habits:
                if habit_tostart == habit.name:
                    habit.stopped = False
                    user.send(f"Started {habit.name}!")
                    if habit.interval is None:
                        user.schedule_generator(habit.interval, peck_once(
                            user, habit), expires_in=habit.interval, autocancel=True)
                    else:
                        user.schedule_generator(habit.interval, peck_multiple(
                            user, habit), expires_in=habit.interval, autocancel=True)

        elif 'habits' in msg:
            user.send(habit_to_string(habits))
        elif 'delete' in msg:
            habit_todelete = ""
            if len(msg.split(' ')) > 1:
                for string in msg.split(' '):
                    if string != "habit" and string != "hobby" and string != "delete" and len(new_habit) == 0:
                        habit_todelete = string
                        break
            if len(habit_todelete) == 0:
                user.send(habit_to_string(habits))
                habit_todelete = yield "which habit would you like to delete?"
                habit_deletedyet = False
            for habit in habits:
                if habit.name == habit_todelete:
                    habit.destroyed = True
                    habits.remove(habit)
                    user.send("i deleted " + habit.name + " !")
                    habit_deletedyet = True
            if habit_deletedyet == False:
                user.send(
                    "hmm... it seems like that's not one of your habits. text 'delete' to remove a habit!")
        elif 'update' in msg:
            time_pecks = yield "you want to update the time interval of one your habits, awesome! \n do you want to modify a one-time update habit or a repeating habit? (say 'one-time' or 'recurring')"
            if time_pecks == 'recurring':
                user.send("here are your current recurring habits:")
                habList = ''
                for habit in habits:
                    if habit.interval != None:
                        habList += "habit: " + habit.name + " | interval: " + \
                            str(habit.interval) + " seconds \n"
                user.send(habList)
                name_tomodify = yield "which habit do you want to update the time interval for?"
                new_interval_str = yield "what do you want the new time interval to be (in seconds)?"
                try:
                    new_interval = int(new_interval_str)
                except ValueError:
                    user.send(
                        "I'm not quite sure what you mean by that! Please try again!")
                    continue

                habit_deletedyet = False
                for habit in habits:
                    if habit.name == name_tomodify:
                        # add new one
                        habit = Habit(user_id, habit.name,
                                      new_interval)
                        habits.append(habit)
                    # destroy old one
                        habit.destroyed = True
                        habits.remove(habit)
                        habit_deletedyet = True
                if habit_deletedyet == False:
                    user.send(
                        "hmm... it seems like that's not one of your habits. text 'delete' to remove a habit!")
            elif 'one-time' in time_pecks:
                user.send("here are your current one-time reminder habits:")
                habList = ''
                for habit in habits:
                    if habit.interval == None:
                        habList += "habit: " + habit.name + " | interval: " + \
                            str(habit.interval) + " seconds \n"
                user.send(habList)
                name_tomodify = yield "which habit do you want to update the one-time reminder for?"
                new_interval_str = yield "in how long do you want to be reminded (in seconds)?"
                try:
                    new_interval = int(new_interval_str)
                except ValueError:
                    user.send(
                        "I'm not quite sure what you mean by that! Please try again!")
                    continue

                habit_deletedyet = False
                for habit in habits:
                    if habit.name == name_tomodify:
                        # add new one
                        habit = Habit(user_id, habit.name)
                        habits.append(habit)
                        user.schedule_generator(new_interval, peck_once(
                            user, habit), expires_in=new_interval, autocancel=True)
                    # destroy old one
                        habit.destroyed = True
                        habits.remove(habit)
                        habit_deletedyet = True
                if habit_deletedyet == False:
                    user.send(
                        "hmm... it seems like that's not one of your habits. text 'delete' to remove a habit!")
            else:
                user.send(
                    "that's not one of the time types, silly! if you still want to delete something type 'delete' again!")

            # this will be deleted:
            name_tomodify = yield "which habit do you want to update the time interval for?"
            new_interval = yield "what do you want the new time interval to be (in seconds)?"
            for habit in habits:
                if habit.name == name_tomodify:
                    habits.interval = new_interval
                    user.send("i updated " + habit.name +
                              " to now remind you every " + habit.interval + " seconds!")

            # until hereeee
        else:
            user.send("unknown command :( try again!")
