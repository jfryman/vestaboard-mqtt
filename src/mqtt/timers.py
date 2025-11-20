"""Timer management for timed messages."""

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..vestaboard.local_client import LocalVestaboardClient

if TYPE_CHECKING:
    from ..state import SaveStateManager
    from ..vestaboard import BaseVestaboardClient


class TimerManager:
    """Manages timed messages with auto-restore functionality."""

    def __init__(
        self,
        vestaboard_client: "BaseVestaboardClient",
        save_state_manager: "SaveStateManager",
        restore_callback,
    ):
        """Initialize the timer manager.

        Args:
            vestaboard_client: Vestaboard client for rate limit checks
            save_state_manager: State manager for saving/restoring
            restore_callback: Callback function to restore from slot
        """
        self.vestaboard_client = vestaboard_client
        self.save_state_manager = save_state_manager
        self.restore_callback = restore_callback
        self.active_timers: Dict[str, threading.Timer] = {}
        self.logger = logging.getLogger(__name__)

    def schedule_timed_message(
        self,
        message: str,
        duration_seconds: int,
        restore_slot: Optional[str] = None,
        strategy: Optional[str] = None,
        step_interval_ms: Optional[int] = None,
        step_size: Optional[int] = None,
        restore_strategy: Optional[str] = None,
        restore_step_interval_ms: Optional[int] = None,
        restore_step_size: Optional[int] = None,
    ) -> str:
        """Schedule a timed message with optional auto-restore and animation.

        Args:
            message: Message to display
            duration_seconds: How long to display the message
            restore_slot: Optional slot to restore from after timer expires
            strategy: Optional animation strategy for timed message (Local API)
            step_interval_ms: Optional delay between animation steps for timed message (1-60000ms)
            step_size: Optional number of updates for timed message (1-132)
            restore_strategy: Optional animation strategy for restore (defaults to strategy)
            restore_step_interval_ms: Optional delay for restore (defaults to step_interval_ms)
            restore_step_size: Optional size for restore (defaults to step_size)

        Returns:
            Timer ID for cancellation
        """
        timer_id = f"timer_{int(time.time())}"

        # Save current state if no restore slot specified
        if restore_slot is None:
            restore_slot = f"temp_{timer_id}"
            self.save_state_manager.save_current_state(restore_slot)

        # Determine if animation is requested and supported
        use_animation = strategy and isinstance(self.vestaboard_client, LocalVestaboardClient)

        # Display the timed message
        if use_animation:
            success = self.vestaboard_client.write_animated_message(
                message=message,
                strategy=strategy,
                step_interval_ms=step_interval_ms,
                step_size=step_size,
            )
            message_type = f"animated timed message (strategy={strategy})"
        else:
            if strategy:
                self.logger.warning(
                    f"Animation strategy '{strategy}' ignored - only supported with Local API"
                )
            success = self.vestaboard_client.write_message(message)
            message_type = "timed message"

        if not success:
            self.logger.error(f"Failed to display {message_type}")
            return timer_id

        self.logger.info(f"Successfully sent {message_type}")

        # Record when we wrote the timed message for rate limit tracking
        write_time = time.time()

        # Default restore animation params to timed message params if not specified
        final_restore_strategy = restore_strategy if restore_strategy is not None else strategy
        final_restore_step_interval_ms = (
            restore_step_interval_ms if restore_step_interval_ms is not None else step_interval_ms
        )
        final_restore_step_size = (
            restore_step_size if restore_step_size is not None else step_size
        )

        # Schedule restoration
        def restore_previous():
            """Restore callback executed after timer expires."""
            self.logger.info(f"Timer {timer_id} expired, restoring from slot {restore_slot}")

            # Respect rate limits before restoring
            self._wait_for_rate_limit(write_time)

            self.restore_callback(
                restore_slot,
                strategy=final_restore_strategy,
                step_interval_ms=final_restore_step_interval_ms,
                step_size=final_restore_step_size,
            )

            # Clean up timer tracking
            self.active_timers.pop(timer_id, None)

        timer = threading.Timer(duration_seconds, restore_previous)
        self.active_timers[timer_id] = timer
        timer.start()

        self.logger.info(f"Scheduled timed message for {duration_seconds} seconds (ID: {timer_id})")
        return timer_id

    def cancel_timed_message(self, timer_id: str) -> bool:
        """Cancel a scheduled timed message.

        Args:
            timer_id: ID of timer to cancel

        Returns:
            True if cancelled, False if not found
        """
        timer = self.active_timers.pop(timer_id, None)
        if timer is not None:
            timer.cancel()
            self.logger.info(f"Cancelled timer {timer_id}")
            return True
        return False

    def get_timer_info_list(self) -> list[Dict[str, Any]]:
        """Build list of active timer information.

        Returns:
            List of timer info dictionaries
        """
        timer_info = []
        for timer_id, timer in self.active_timers.items():
            # Note: Timer objects don't expose remaining time directly
            # This is a limitation of threading.Timer
            created_at = timer_id.split("_")[-1] if "_" in timer_id else "unknown"
            timer_info.append(
                {
                    "timer_id": timer_id,
                    "active": timer.is_alive(),
                    "created_at": created_at,
                }
            )
        return timer_info

    def cleanup_all_timers(self):
        """Cancel all active timers."""
        for timer_id, timer in list(self.active_timers.items()):
            timer.cancel()
            self.logger.debug(f"Cancelled timer {timer_id}")
        self.active_timers.clear()

    def _wait_for_rate_limit(self, write_time: float) -> None:
        """Wait for rate limit to clear if necessary.

        Args:
            write_time: Timestamp of the last write operation
        """
        if not hasattr(self.vestaboard_client, "RATE_LIMIT_SECONDS"):
            return

        rate_limit = self.vestaboard_client.RATE_LIMIT_SECONDS
        time_since_write = time.time() - write_time
        remaining_wait = rate_limit - time_since_write

        if remaining_wait > 0:
            self.logger.info(
                f"Waiting {remaining_wait:.1f}s for Cloud API rate limit before restore"
            )
            time.sleep(remaining_wait + 0.5)  # Add 0.5s buffer
