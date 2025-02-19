import arrow
import pytest
from app.utils.schedule import Schedule, check_and_revert_snooze, get_current_schedule_time, get_schedule, snooze_schedule
from datetime import UTC, datetime, timedelta, timezone
from pony.orm import Database, Optional, PrimaryKey, Required, commit, db_session, flush
from unittest.mock import MagicMock, patch


def strip_timezone(dt):
    """Helper function to convert datetime to naive UTC"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.replace(tzinfo=None)


@pytest.fixture
def test_db():
    """Create a test database"""
    db = Database()
    return db


@pytest.fixture
def TestSchedule(test_db):
    """Create TestSchedule Entity class"""
    class TestSchedule(test_db.Entity):
        _table_ = "schedule"
        id = PrimaryKey(int, auto=True)
        day = Required(str, unique=True)
        schedule_time = Required(str)
        timezone = Required(str)
        enabled = Required(bool, default=True)
        snooze_until = Optional(datetime)
        original_schedule_time = Optional(str, nullable=True)
        last_changed = Required(datetime, default=datetime.utcnow)

    test_db.bind(provider="sqlite", filename=":memory:")
    test_db.generate_mapping(create_tables=True)

    yield TestSchedule

    # Clean up after each test
    test_db.drop_all_tables(with_all_data=True)
    test_db.disconnect()


@pytest.fixture
def mock_schedule(TestSchedule):
    """Create a test schedule"""
    with db_session:
        schedule = TestSchedule(
            day="Monday",
            schedule_time="10:00",
            timezone="UTC",
            enabled=True,
        )
        commit()
        return schedule


def test_get_schedule(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        mock_now.return_value = arrow.get('2025-01-01T10:00:00+00:00')
        schedule = get_schedule("Monday")
        assert schedule is not None
        assert schedule.day == "Monday"
        assert schedule.schedule_time == "10:00"
        assert schedule.enabled is True


def test_get_schedule_nonexistent_day(TestSchedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         db_session:
        schedule = get_schedule("InvalidDay")
        assert schedule is None


def test_get_current_schedule_time(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now:
        mock_now.return_value = arrow.get('2025-01-01T10:00:00+00:00')
        utc_time, local_time = get_current_schedule_time(mock_schedule)

        assert isinstance(utc_time, str)
        assert isinstance(local_time, str)
        assert utc_time == "10:00"
        assert local_time == "10:00"


def test_snooze_schedule_5_minutes(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        current_time = arrow.get('2025-01-01T10:00:00+00:00')
        mock_now.return_value = current_time

        schedule = get_schedule("Monday")
        original_time = schedule.schedule_time
        snooze_schedule(schedule, "5_minutes")

        assert schedule.snooze_until is not None
        assert schedule.original_schedule_time == original_time

        expected_time = current_time.shift(minutes=5)
        actual_time = arrow.get(schedule.snooze_until)

        # Compare only the minute difference
        time_diff = (actual_time - current_time).total_seconds()
        assert 290 < time_diff < 310  # Allow for small variations around 5 minutes


def test_snooze_schedule_next_scheduled(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        current_time = arrow.get('2025-01-01T11:00:00+00:00')
        mock_now.return_value = current_time

        schedule = get_schedule("Monday")
        original_time = schedule.schedule_time
        snooze_schedule(schedule, "next_scheduled")
        commit()

        # Re-fetch schedule in new transaction
        with db_session:
            schedule = get_schedule("Monday")
            assert schedule.snooze_until is not None
            assert schedule.original_schedule_time == original_time

            # Convert to naive UTC datetime for comparison
            snooze_time = arrow.get(schedule.snooze_until).naive
            expected_time = arrow.get('2025-01-02T10:00:00+00:00').naive
            assert snooze_time == expected_time


def test_snooze_schedule_rest_of_week(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        # Use Monday January 6th, 2025
        current_time = arrow.get('2025-01-06T10:00:00+00:00')  # A Monday
        mock_now.return_value = current_time

        schedule = get_schedule("Monday")
        original_time = schedule.schedule_time
        snooze_schedule(schedule, "rest_of_week")
        commit()

        # Re-fetch schedule in new transaction
        with db_session:
            schedule = get_schedule("Monday")
            assert schedule.snooze_until is not None
            assert schedule.original_schedule_time == original_time

            # Convert to naive UTC datetime for comparison
            snooze_time = arrow.get(schedule.snooze_until).naive
            # Next Sunday (Jan 12) at midnight
            expected_time = arrow.get('2025-01-12T00:00:00+00:00').naive
            assert snooze_time == expected_time


def test_snooze_schedule_invalid_duration(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         db_session:
        schedule = get_schedule("Monday")
        with pytest.raises(ValueError):
            snooze_schedule(schedule, "invalid_duration")


def test_check_and_revert_snooze_expired(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        current_time = arrow.get('2025-01-01T10:00:00+00:00')
        mock_now.return_value = current_time

        # Setup initial state
        schedule = get_schedule("Monday")
        past_time = current_time.shift(minutes=-5).naive
        schedule.snooze_until = past_time
        schedule.original_schedule_time = "10:00"
        schedule.schedule_time = "15:00"
        flush()  # Ensure changes are saved without committing transaction

        # Run check in same transaction
        check_and_revert_snooze()
        commit()

        # Verify in same transaction
        schedule = get_schedule("Monday")
        assert schedule.snooze_until is None
        assert schedule.original_schedule_time is None
        assert schedule.schedule_time == "10:00"


def test_check_and_revert_snooze_future(TestSchedule, mock_schedule):
    with patch('app.utils.schedule.Schedule', TestSchedule), \
         patch('app.utils.schedule.TZ', 'UTC'), \
         patch('app.utils.schedule.LOCAL_TIME', '10:00'), \
         patch('arrow.now') as mock_now, \
         db_session:
        current_time = arrow.get('2025-01-01T10:00:00+00:00')
        mock_now.return_value = current_time

        # Setup initial state
        schedule = get_schedule("Monday")
        future_time = current_time.shift(minutes=5).naive
        schedule.snooze_until = future_time
        schedule.original_schedule_time = "10:00"
        schedule.schedule_time = "15:00"
        flush()  # Ensure changes are saved without committing transaction

        # Run check in same transaction
        check_and_revert_snooze()
        commit()

        # Verify in same transaction
        schedule = get_schedule("Monday")
        assert schedule.snooze_until is not None
        assert schedule.original_schedule_time == "10:00"
        assert schedule.schedule_time == "15:00"
