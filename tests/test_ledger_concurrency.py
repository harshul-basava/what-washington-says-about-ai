"""Readers must see complete cost records while parallel workers append them."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import llm


class LedgerConcurrencyTests(unittest.TestCase):
    def test_readers_wait_until_the_cost_record_is_complete(self):
        for reader in (llm.spent, llm.spent_this_month):
            with self.subTest(reader=reader.__name__), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'ledger.jsonl'
                path.write_text('')
                prefix_written, release = threading.Event(), threading.Event()

                class SlowAppend:
                    def __enter__(self):
                        self.file = path.open('a')
                        return self

                    def write(self, value):
                        self.file.write(value[:40]); self.file.flush()
                        prefix_written.set()
                        if not release.wait(5):
                            raise TimeoutError('Test did not release the append')
                        self.file.write(value[40:])

                    def __exit__(self, *args):
                        self.file.close()

                class LedgerPath:
                    parent = path.parent
                    def exists(self): return path.exists()
                    def read_text(self): return path.read_text()
                    def open(self, mode):
                        return SlowAppend()

                with patch.object(llm, 'LEDGER', LedgerPath()), ThreadPoolExecutor(max_workers=2) as pool:
                    writer = pool.submit(llm._log, 'openrouter', .25, 'daily_test', {})
                    self.assertTrue(prefix_written.wait(2))
                    reading = pool.submit(reader, 'openrouter')
                    try:
                        # A completed reader here saw only a partial JSON record.
                        self.assertFalse(reading.done() or reading.exception(timeout=.05))
                    except TimeoutError:
                        pass
                    finally:
                        release.set()
                    writer.result(timeout=2)
                    self.assertAlmostEqual(reading.result(timeout=2), .25)


if __name__ == '__main__':
    unittest.main()
