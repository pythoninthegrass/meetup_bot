#!/usr/bin/env python

import arrow
import time
from datetime import datetime, timedelta
from decouple import config
from pony.orm import Database, Optional, PrimaryKey, Required, Set, commit, db_session

# env
DB_NAME = config("DB_NAME")
DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT", default=5432, cast=int)
TZ = config("TZ", default="America/Chicago")        # Set this to local timezone
LOCAL_TIME = config("LOCAL_TIME", default="09:00")  # Local time for schedule

# time
loc_time = arrow.now().to(TZ)
time.tzset()
days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
enabled_days = ["Monday", "Wednesday", "Friday"]

# init db
db = Database()


# schedule model
class Schedule(db.Entity):
    _table_ = "schedule"
    id = PrimaryKey(int, auto=True)
    day = Required(str, unique=True)
    schedule_time = Required(str)
    timezone = Required(str)
    enabled = Required(bool, default=True)
    snooze_until = Optional(datetime)
    original_schedule_time = Optional(str)
    last_changed = Required(datetime, default=datetime.utcnow)


# strip double quotes from string
DB_PASS = DB_PASS.strip('"')

# postgres db
db.bind(provider="postgres", user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME, port=DB_PORT, sslmode="require")

# generate mapping
db.generate_mapping(create_tables=True)


def local_to_utc(local_time_str, timezone):
    """Convert local time to UTC"""
    local_time = arrow.get(local_time_str, "HH:mm")
    local_datetime = arrow.now(timezone).replace(hour=local_time.hour, minute=local_time.minute)
    utc_datetime = local_datetime.to("UTC")
    return utc_datetime.format("HH:mm")


def get_current_schedule_time(schedule):
    """Get the current schedule time in both UTC and the local timezone"""
    utc_time = schedule.schedule_time
    local_time = LOCAL_TIME
    return utc_time, local_time


@db_session
def update_schedule(day, timezone=None, enabled=None):
    """Update the schedule for a specific day"""
    schedule = Schedule.get(day=day)
    updated = False

    if schedule:
        if timezone is not None and schedule.timezone != timezone:
            schedule.timezone = timezone
            updated = True

        # Always check and update the enabled status
        should_be_enabled = day in enabled_days
        if schedule.enabled != should_be_enabled:
            schedule.enabled = should_be_enabled
            updated = True
            print(f"Updated {day}: enabled = {should_be_enabled}")

        if updated:
            schedule.last_changed = datetime.utcnow()
            print(f"Updated schedule for {day}")
        else:
            print(f"No changes needed for {day}")
    else:
        utc_time = local_to_utc(LOCAL_TIME, timezone or TZ)
        Schedule(
            day=day,
            schedule_time=utc_time.format("HH:mm"),
            timezone=timezone or TZ,
            enabled=day in enabled_days,
        )
        print(f"Created schedule for {day}")


@db_session
def initialize_schedule():
    """Initialize the schedule table with default values"""
    for day in days:
        update_schedule(day)


@db_session
def update_all_schedules(new_timezone=None):
    """Update all schedules with new timezone"""
    if new_timezone is None:
        print("No updates provided. Skipping update operation.")
        return

    for day in days:
        update_schedule(day, timezone=new_timezone)


@db_session
def get_schedule(day):
    """Get the schedule for a specific day"""
    return Schedule.get(day=day)


@db_session
def snooze_schedule(schedule, duration):
    """Snooze the schedule for the specified duration"""
    current_time = arrow.now(TZ)
    # Compute today's scheduled datetime using the stored schedule_time (assumed in HH:mm format)
    # Use the schedule's timezone for the current date
    today_str = arrow.now(schedule.timezone).format('YYYY-MM-DD')
    # Create a datetime for today at the scheduled time
    daily_schedule_time = arrow.get(f"{today_str} {schedule.schedule_time}", "YYYY-MM-DD HH:mm").to(schedule.timezone)

    if duration == "5_minutes":
        snooze_until = current_time.shift(minutes=5)
        new_schedule_time = snooze_until.to("UTC").format("HH:mm")
    elif duration == "next_scheduled":
        snooze_until = daily_schedule_time.shift(days=1) if current_time > daily_schedule_time else daily_schedule_time
        new_schedule_time = schedule.schedule_time
    elif duration == "rest_of_week":
        # For rest_of_week, calculate days until next Sunday.
        # Using (7 - weekday()) % 7 to correctly handle all days including Sunday
        days_until_sunday = (6 - current_time.weekday()) % 7
        snooze_until = current_time.shift(days=days_until_sunday).replace(hour=0, minute=0, second=0, microsecond=0)
        new_schedule_time = schedule.schedule_time
    else:
        raise ValueError("Invalid snooze duration")

    # Store snooze_until as a naive UTC datetime
    schedule.snooze_until = snooze_until.to('UTC').naive
    schedule.original_schedule_time = schedule.schedule_time
    schedule.schedule_time = new_schedule_time
    print(f"Snoozed schedule until {snooze_until.format('YYYY-MM-DD HH:mm:ss')}")
    return schedule


@db_session
def check_and_revert_snooze():
    """Check if any snoozes need to be reverted and revert them if necessary"""
    current_time = arrow.now(TZ)
    current_time_naive = current_time.to('UTC').naive

    # Don't materialize the query before making changes to avoid potential inconsistencies
    for schedule in Schedule.select(lambda s: s.snooze_until is not None):
        if current_time_naive >= schedule.snooze_until:
            schedule.schedule_time = schedule.original_schedule_time
            schedule.snooze_until = None
            schedule.original_schedule_time = None
            print(f"Reverted snooze for {schedule.day}")


@db_session
def check_and_update_env_changes():
    """Check for changes in environment variables and update schedules if necessary"""
    current_timezone = TZ

    print(f"Current environment: LOCAL_TIME={LOCAL_TIME}, TZ={current_timezone}")

    sample_schedule = Schedule.get(day="Monday")
    if sample_schedule:
        print(f"Current database values: TZ={sample_schedule.timezone}")

        if sample_schedule.timezone != current_timezone:
            print("Detected changes in environment variables. Updating schedules...")
            update_all_schedules(new_timezone=current_timezone)
        else:
            print("No changes detected in environment variables.")
    else:
        print("Could not find a sample schedule to check against.")


def main():
    print("Initializing schedule...")
    initialize_schedule()
    print("Schedule initialization complete.")

    print("\nChecking and reverting snoozes...")
    check_and_revert_snooze()

    print("\nChecking for updates to timezone...")
    check_and_update_env_changes()

    print("\nCurrent schedule:")
    max_day_length = max(len(day) for day in days)

    for day in days:
        schedule = get_schedule(day)
        if schedule:
            utc_time, local_time = get_current_schedule_time(schedule)
            status = "[Enabled]" if schedule.enabled else "[Disabled]"
            snooze_info = (
                f" (Snoozed until {schedule.snooze_until}, original time: {schedule.original_schedule_time})"
                if schedule.snooze_until
                else ""
            )
            print(f"{day:<{max_day_length}}: {utc_time} UTC ({local_time} {schedule.timezone}) {status}{snooze_info}")

    local_now = arrow.now(TZ)
    utc_now = arrow.utcnow()
    print(f"\nCurrent time: {utc_now.format('HH:mm')} UTC ({local_now.format('HH:mm')} {TZ})")
    print(f"DST in effect: {bool(local_now.dst())}")
    print(f"UTC offset: {local_now.utcoffset()}")


if __name__ == "__main__":
    main()
