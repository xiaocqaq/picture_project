import threading
import time
from dataclasses import dataclass, field
from typing import Literal


TaskStatus = Literal["queued", "running", "succeeded", "failed"]


class SnowflakeGenerator:
    def __init__(self, worker_id: int = 1):
        if worker_id < 0 or worker_id > 1023:
            raise ValueError("worker_id must be between 0 and 1023")
        self.worker_id = worker_id
        self.epoch_ms = 1704067200000
        self.sequence = 0
        self.last_ms = -1
        self.lock = threading.Lock()

    def next_id(self) -> int:
        with self.lock:
            now = int(time.time() * 1000)
            if now < self.last_ms:
                now = self.last_ms
            if now == self.last_ms:
                self.sequence = (self.sequence + 1) & 0xFFF
                if self.sequence == 0:
                    now = self._wait_next_ms(now)
            else:
                self.sequence = 0
            self.last_ms = now
            return ((now - self.epoch_ms) << 22) | (self.worker_id << 12) | self.sequence

    def _wait_next_ms(self, current_ms: int) -> int:
        now = int(time.time() * 1000)
        while now <= current_ms:
            now = int(time.time() * 1000)
        return now


@dataclass
class GenerationTask:
    task_id: str
    prompt: str
    size: str
    quality: str
    n: int
    status: TaskStatus = "queued"
    progress: int = 0
    images: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "size": self.size,
            "quality": self.quality,
            "n": self.n,
            "status": self.status,
            "progress": self.progress,
            "images": self.images,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, GenerationTask] = {}
        self._lock = threading.Lock()
        self._ids = SnowflakeGenerator()

    def create(self, prompt: str, size: str, quality: str, n: int) -> GenerationTask:
        task = GenerationTask(
            task_id=str(self._ids.next_id()),
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> GenerationTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id: str, **changes) -> GenerationTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = time.time()
            return task


task_store = TaskStore()
