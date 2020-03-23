
from __future__ import annotations

import asyncio, sys, time, functools
from threading import Thread
from typing import Any

def print_progress(title: str) -> callable:
    def decorator(f: callable) -> callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            manager = ProgressManager(title)

            f(*args, **kwargs)
            manager.complete()

        return wrapper
    return decorator

class ProgressManager:
    def __init__(self, title: str) -> None:
        self.title = title
        
        self._indicator_len = 5
        self._progress = 0
        self._completed = False
        self._loop = asyncio.new_event_loop()
        
        self._thread = Thread(target=self.start)
        self._thread.start()
        
        asyncio.run_coroutine_threadsafe(self._prg_loop(), self._loop)

    def _write(self, message: str, clear: bool = True) -> ProgressManager:
        if clear:
            # Clear the current line
            sys.stdout.write('\x1b[2K\r')

        sys.stdout.write(self.title + ' - ' + message)
        sys.stdout.flush()

        return self

    def update_output(self, idx) -> ProgressManager:
        self._write(self._format_indicator(idx))

        return self

    def complete(self) -> ProgressManager:
        self._completed = True

        return self

    def _format_indicator(self, idx: int) -> str:
        cap = self._indicator_len
        return f'[{" " * idx}={" " * (cap - idx)}]'

    async def _prg_loop(self) -> None:
        idx = 0
        incr = True
        
        self._write(self._format_indicator(idx), clear=False)

        while not self._completed:
            self.update_output(idx)
            incr = (incr and idx < self._indicator_len) or idx <= 0

            idx += 1 if incr else -1

            await asyncio.sleep(0.1)

        self._write('Completed\n')

    def start(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

if __name__ == '__main__':
    @print_progress('Installing extDB3')
    def main():
        time.sleep(5)

    @print_progress('Building @life_server')
    def main_1():
        time.sleep(2)

    main()
    main_1()