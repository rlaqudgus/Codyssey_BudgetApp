"""서비스/저장소/데코레이터 단위 테스트."""

from __future__ import annotations

import inspect
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import date, timedelta
from pathlib import Path

from budget_app.decorators import handle_errors
from budget_app.errors import NotFoundError
from budget_app.formatting import display_width, render_table
from budget_app.models import NewTransaction, Transaction, TxType, format_tx_id
from budget_app.services.transaction_service import latest_first
from budget_app.storage import TransactionRepository
from budget_app.storage.jsonl import JsonlFile


class StreamingTest(unittest.TestCase):
    def test_repository_reads_with_generator(self) -> None:
        self.assertTrue(inspect.isgeneratorfunction(TransactionRepository.iter_all))
        self.assertTrue(inspect.isgeneratorfunction(JsonlFile._numbered))

    def test_latest_first_consumes_stream_once(self) -> None:
        start = date(2024, 1, 1)
        consumed = 0

        def stream():  # 10만 건을 흘려보내도 결과는 limit 건만 유지
            nonlocal consumed
            for i in range(100_000):
                consumed += 1
                yield Transaction(format_tx_id(i + 1), TxType.EXPENSE, start + timedelta(days=i % 365), 1, "food")

        result = latest_first(stream(), 3)
        self.assertEqual(consumed, 100_000)
        self.assertEqual(result.total, 100_000)
        self.assertEqual(len(result.items), 3)
        self.assertTrue(all(tx.date == date(2024, 12, 30) for tx in result.items))


class AtomicRewriteTest(unittest.TestCase):
    def test_failure_midway_keeps_original_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = TransactionRepository(Path(tmp))
            repo.add(NewTransaction(TxType.EXPENSE, date(2024, 1, 1), 100, "food"))
            original = repo.file.path.read_text(encoding="utf-8")

            def broken():
                yield {"id": "TX-000001"}
                raise RuntimeError("디스크 오류 흉내")

            with self.assertRaises(RuntimeError):
                repo.file.rewrite(broken())
            self.assertEqual(repo.file.path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])


class DecoratorTest(unittest.TestCase):
    def test_handle_errors_converts_exceptions_to_exit_codes(self) -> None:
        @handle_errors
        def not_found() -> int:
            raise NotFoundError("없음", "힌트")

        @handle_errors
        def unexpected() -> int:
            raise ZeroDivisionError("boom")

        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(not_found(), 3)
            self.assertEqual(unexpected(), 1)
        self.assertIn("[오류] 없음", err.getvalue())
        self.assertIn("[힌트] 힌트", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


class FormattingTest(unittest.TestCase):
    def test_korean_is_double_width(self) -> None:
        self.assertEqual(display_width("점심"), 4)
        lines = render_table(("메모", "x"), [["점심", "1"], ["lunch", "2"]]).splitlines()
        # 한글 행과 영문 행의 구분자(|)가 화면상 같은 열에 위치해야 한다.
        widths = {display_width(line.split("|")[0]) for line in (lines[0], lines[2], lines[3])}
        self.assertEqual(len(widths), 1)


if __name__ == "__main__":
    unittest.main()
