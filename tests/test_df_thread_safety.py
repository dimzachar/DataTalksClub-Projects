"""Tests for thread-safe DataFrame updates in generate_titles_and_classify."""

import time
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytest


class TestDataFrameThreadSafety:
    """Tests to verify thread-safe DataFrame updates."""

    def test_concurrent_updates_with_lock(self):
        """Test that concurrent updates with lock don't lose data."""
        df = pd.DataFrame({'value': [None] * 100})
        lock = Lock()

        def update_row(index):
            time.sleep(0.001)  # Simulate some work
            with lock:
                df.at[index, 'value'] = f"updated_{index}"
            return index

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_row, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()

        # All rows should be updated
        assert df['value'].notna().all()
        # Each row should have correct value
        for i in range(100):
            assert df.at[i, 'value'] == f"updated_{i}"

    def test_concurrent_updates_without_lock_can_fail(self):
        """Demonstrate that updates without lock can have issues.

        Note: This test may pass sometimes due to timing, but demonstrates
        the potential for race conditions.
        """
        df = pd.DataFrame({'counter': [0]})

        def increment_without_lock():
            for _ in range(100):
                current = df.at[0, 'counter']
                time.sleep(0.0001)  # Increase chance of race condition
                df.at[0, 'counter'] = current + 1

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(increment_without_lock) for _ in range(4)]
            for future in as_completed(futures):
                future.result()

        # Without lock, final value is likely less than 400 due to race conditions
        # We don't assert failure here as it's non-deterministic
        # This test documents the issue rather than enforcing it
        final_value = df.at[0, 'counter']
        # Just verify it ran
        assert final_value > 0

    def test_concurrent_updates_with_lock_are_correct(self):
        """Test that updates with lock produce correct results."""
        df = pd.DataFrame({'counter': [0]})
        lock = Lock()

        def increment_with_lock():
            for _ in range(100):
                with lock:
                    current = df.at[0, 'counter']
                    df.at[0, 'counter'] = current + 1

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(increment_with_lock) for _ in range(4)]
            for future in as_completed(futures):
                future.result()

        # With lock, final value should be exactly 400
        assert df.at[0, 'counter'] == 400


class TestCounterThreadSafety:
    """Tests for the Counter class thread safety."""

    def test_counter_concurrent_increments(self):
        """Test Counter class handles concurrent increments correctly."""
        from src.generate_titles_and_classify import Counter

        counter = Counter()

        def increment_all():
            for _ in range(100):
                counter.inc_success()
                counter.inc_skip()
                counter.inc_error()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(increment_all) for _ in range(4)]
            for future in as_completed(futures):
                future.result()

        assert counter.success == 400
        assert counter.skip == 400
        assert counter.error == 400
