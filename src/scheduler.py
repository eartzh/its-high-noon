import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any, Optional, Dict, List
from uuid import uuid4, UUID

import schedule

LOGGER = logging.getLogger("scheduler")


@dataclass
class ScheduledCallback:
    """Represents a scheduled callback with its configuration."""
    id: UUID
    callback: Callable[..., Any]
    schedule_time: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    callback_kwargs: Dict[str, Any] = None

    def __post_init__(self):
        if self.callback_kwargs is None:
            self.callback_kwargs = {}


class Scheduler:
    def __init__(self):
        """Initialize the Scheduler."""
        self.callbacks: Dict[UUID, ScheduledCallback] = {}
        self.scheduler_thread = None
        self.is_running = False
        self._lock = threading.Lock()

    def register(
            self,
            callback: Callable[..., Any],
            schedule_time: str,
            enabled: bool = True,
            **callback_kwargs
    ) -> UUID:
        """
        Add a new callback to be executed at the specified time.

        Args:
            callback (Callable): The function to be called at the scheduled time
            schedule_time (str): Time to schedule daily callback (UTC+0, 24-hour format, e.g. "08:00")
            enabled (bool): Whether the callback should be enabled immediately
            **callback_kwargs: Additional keyword arguments to pass to the callback function

        Returns:
            UUID: Unique identifier for the scheduled callback
        """
        callback_id = uuid4()

        with self._lock:
            scheduled_callback = ScheduledCallback(
                id=callback_id,
                callback=callback,
                schedule_time=schedule_time,
                enabled=enabled,
                callback_kwargs=callback_kwargs
            )

            # Add to the schedule library
            job = schedule.every().day.at(schedule_time).do(
                self.execute_callback,
                callback_id=callback_id
            )

            # Set the next run time
            scheduled_callback.next_run = job.next_run

            # Store in our callbacks dictionary
            self.callbacks[callback_id] = scheduled_callback

            LOGGER.info(f"Added new callback with ID {callback_id} scheduled for {schedule_time}")

        return callback_id

    def remove_callback(self, callback_id: UUID) -> bool:
        """
        Remove a callback from the scheduler.

        Args:
            callback_id (UUID): The ID of the callback to remove

        Returns:
            bool: True if callback was removed, False if not found
        """
        with self._lock:
            if callback_id in self.callbacks:
                # Remove all jobs matching this callback_id
                schedule.clear(tag=str(callback_id))
                del self.callbacks[callback_id]
                LOGGER.info(f"Removed callback with ID {callback_id}")
                return True
            return False

    def execute_callback(self, callback_id: UUID) -> bool:
        """Execute a specific callback and handle any errors."""
        try:
            with self._lock:
                if callback_id not in self.callbacks:
                    LOGGER.error(f"Callback {callback_id} not found")
                    return False

                scheduled_callback = self.callbacks[callback_id]
                if not scheduled_callback.enabled:
                    LOGGER.info(f"Skipping disabled callback {callback_id}")
                    return True

            execution_time = datetime.now()

            # Execute the callback
            scheduled_callback.callback(**scheduled_callback.callback_kwargs)

            with self._lock:
                if callback_id in self.callbacks:  # Check again in case removed during execution
                    self.callbacks[callback_id].last_run = execution_time
                    # Update next run time
                    matching_jobs = [job for job in schedule.jobs if str(callback_id) in str(job.tags)]
                    if matching_jobs:
                        self.callbacks[callback_id].next_run = matching_jobs[0].next_run

            LOGGER.info(f"Callback {callback_id} executed successfully at {execution_time}")
            return True

        except Exception as e:
            LOGGER.error(f"Failed to execute callback {callback_id}: {str(e)}")
            return False

    def enable_callback(self, callback_id: UUID) -> bool:
        """Enable a callback."""
        with self._lock:
            if callback_id in self.callbacks:
                self.callbacks[callback_id].enabled = True
                LOGGER.info(f"Enabled callback {callback_id}")
                return True
            return False

    def disable_callback(self, callback_id: UUID) -> bool:
        """Disable a callback."""
        with self._lock:
            if callback_id in self.callbacks:
                self.callbacks[callback_id].enabled = False
                LOGGER.info(f"Disabled callback {callback_id}")
                return True
            return False

    def _run_scheduler(self):
        """Run the scheduler loop."""
        self.is_running = True
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                LOGGER.error(f"Scheduler error: {str(e)}")
                time.sleep(60)

    def start(self):
        """Start the scheduler in a background thread."""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            LOGGER.info("Scheduler started in background thread")
        else:
            LOGGER.warning("Scheduler is already running")

    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=2)
            LOGGER.info("Scheduler stopped")

    def get_callback_status(self, callback_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the status of a specific callback."""
        with self._lock:
            if callback_id not in self.callbacks:
                return None

            callback = self.callbacks[callback_id]
            return {
                "id": str(callback.id),
                "schedule_time": callback.schedule_time,
                "enabled": callback.enabled,
                "last_run": callback.last_run.isoformat() if callback.last_run else None,
                "next_run": callback.next_run.isoformat() if callback.next_run else None
            }

    def get_all_callbacks(self) -> List[Dict[str, Any]]:
        """Get status information for all callbacks."""
        with self._lock:
            return [self.get_callback_status(callback_id) for callback_id in self.callbacks]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall scheduler status."""
        return {
            "is_running": self.is_running,
            "callback_count": len(self.callbacks),
            "callbacks": self.get_all_callbacks()
        }