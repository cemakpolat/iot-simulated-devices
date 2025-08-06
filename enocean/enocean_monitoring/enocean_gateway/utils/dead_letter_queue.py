
# utils/dead_letter_queue.py
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from queue import Queue, Empty

from enocean_gateway.utils import Logger


@dataclass
class DeadLetterMessage:
    """Message stored in dead letter queue"""
    id: str
    timestamp: float
    original_function: str
    args: tuple
    kwargs: dict
    exception_type: str
    exception_message: str
    retry_count: int = 0
    max_retries: int = 3


class DeadLetterQueue:
    """Dead letter queue for failed operations"""

    def __init__(self, storage_path: str, logger: Logger, max_size: int = 1000):
        self.storage_path = Path(storage_path)
        self.logger = logger
        self.max_size = max_size

        self._queue = Queue(maxsize=max_size)
        self._storage_lock = threading.Lock()
        self._running = False
        self._processor_thread = None

        self._load_from_storage()

    def add_message(self, function_name: str, args: tuple, kwargs: dict,
                    exception: Exception, max_retries: int = 3):
        """Add failed operation to dead letter queue"""
        message = DeadLetterMessage(
            id=f"{function_name}_{int(time.time() * 1000)}_{id(exception)}",
            timestamp=time.time(),
            original_function=function_name,
            args=args,
            kwargs=kwargs,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            max_retries=max_retries
        )

        try:
            self._queue.put_nowait(message)
            self.logger.warning(f"Added message to dead letter queue: {message.id}")
            self._save_to_storage()
        except:
            self.logger.error(f"Dead letter queue is full, dropping message: {message.id}")

    def start_processor(self, retry_function: Callable[[DeadLetterMessage], bool]):
        """Start background processor for dead letter messages"""
        if self._running:
            return

        self._running = True
        self._processor_thread = threading.Thread(
            target=self._process_messages,
            args=(retry_function,),
            daemon=True
        )
        self._processor_thread.start()
        self.logger.info("Dead letter queue processor started")

    def stop_processor(self):
        """Stop background processor"""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
        self.logger.info("Dead letter queue processor stopped")

    def _process_messages(self, retry_function: Callable[[DeadLetterMessage], bool]):
        """Background processor for retry attempts"""
        while self._running:
            try:
                # Get message with timeout
                message = self._queue.get(timeout=1.0)

                # Check if message should be retried
                if message.retry_count >= message.max_retries:
                    self.logger.error(f"Message {message.id} exceeded max retries, dropping")
                    continue

                # Attempt retry
                try:
                    success = retry_function(message)
                    if success:
                        self.logger.info(f"Successfully retried message {message.id}")
                    else:
                        # Increment retry count and re-queue
                        message.retry_count += 1
                        if message.retry_count < message.max_retries:
                            time.sleep(2 ** message.retry_count)  # Exponential backoff
                            self._queue.put(message)
                        else:
                            self.logger.error(f"Message {message.id} failed final retry")

                except Exception as e:
                    self.logger.error(f"Error processing dead letter message {message.id}: {e}")
                    message.retry_count += 1
                    if message.retry_count < message.max_retries:
                        self._queue.put(message)

                self._save_to_storage()

            except Empty:
                continue  # Timeout, check if still running
            except Exception as e:
                self.logger.error(f"Error in dead letter queue processor: {e}")

    def _load_from_storage(self):
        """Load messages from persistent storage"""
        if not self.storage_path.exists():
            return

        try:
            with self._storage_lock:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)

                for msg_data in data.get('messages', []):
                    message = DeadLetterMessage(**msg_data)
                    try:
                        self._queue.put_nowait(message)
                    except:
                        break  # Queue is full

                self.logger.info(f"Loaded {self._queue.qsize()} messages from dead letter storage")

        except Exception as e:
            self.logger.error(f"Error loading dead letter queue from storage: {e}")

    def _save_to_storage(self):
        """Save current queue state to persistent storage"""
        try:
            with self._storage_lock:
                messages = []
                temp_queue = Queue()

                # Drain queue to get all messages
                while True:
                    try:
                        message = self._queue.get_nowait()
                        messages.append(asdict(message))
                        temp_queue.put(message)
                    except Empty:
                        break

                # Restore queue
                while not temp_queue.empty():
                    self._queue.put(temp_queue.get())

                # Save to file
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, 'w') as f:
                    json.dump({'messages': messages}, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving dead letter queue to storage: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get dead letter queue statistics"""
        return {
            "queue_size": self._queue.qsize(),
            "max_size": self.max_size,
            "processor_running": self._running,
            "storage_path": str(self.storage_path)
        }

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages currently in queue (for monitoring)"""
        messages = []
        temp_queue = Queue()

        # Drain queue to inspect messages
        while True:
            try:
                message = self._queue.get_nowait()
                messages.append(asdict(message))
                temp_queue.put(message)
            except Empty:
                break

        # Restore queue
        while not temp_queue.empty():
            self._queue.put(temp_queue.get())

        return messages


