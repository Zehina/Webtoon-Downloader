from concurrent.futures import ThreadPoolExecutor
import queue
class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, maxsize=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)