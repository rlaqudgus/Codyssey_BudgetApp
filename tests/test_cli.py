"""CLI 통합 테스트: 실제 명령을 임시 데이터 폴더에서 실행해 결과/종료 코드를 확인한다.

실행: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from budget_app.cli.app import main

ROOT = Path(__file__).resolve().parent.parent


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name) / "data"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *argv: str, inputs: list[str] | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        answers = iter(inputs or [])

        def fake_input(prompt: str = "") -> str:
            out.write(prompt)
            try:
                return next(answers)
            except StopIteration:
                raise EOFError from None

        with patch("builtins.input", fake_input), redirect_stdout(out), redirect_stderr(err):
            try:
                code = main([*argv, "--data-dir", str(self.data_dir)])
            except SystemExit as exc:  # argparse 오류/--help
                code = int(exc.code or 0)
        return code, out.getvalue(), err.getvalue()

    def add(self, date: str, type_: str, category: str, amount: str, memo: str = "", tags: str = "") -> str:
        code, out, err = self.run_cli("add", inputs=[date, type_, category, amount, memo, tags])
        self.assertEqual(code, 0, err)
        return out.strip().splitlines()[-1].split("id=")[-1] if "id=" in out else ""

    def tx_ids(self, out: str) -> list[str]:
        return [line.split()[0] for line in out.splitlines() if line.startswith("TX-")]


class InitTest(CliTestCase):
    def test_first_run_creates_files_and_default_categories(self) -> None:
        code, out, _ = self.run_cli("category", "list")
        self.assertEqual(code, 0)
        for name in ("transactions.jsonl", "categories.jsonl", "budgets.jsonl"):
            self.assertTrue((self.data_dir / name).exists(), name)
        self.assertIn("기본 카테고리", out)
        self.assertIn("- food", out)

    def test_help_is_available_for_every_command(self) -> None:
        for command in ("add", "list", "search", "update", "delete", "summary",
                        "budget", "category", "import", "export", "backup", "recurring"):
            code, out, _ = self.run_cli(command, "--help")
            self.assertEqual(code, 0, command)
            self.assertIn("usage:", out)


class AddListTest(CliTestCase):
    def test_add_prints_generated_id(self) -> None:
        code, out, _ = self.run_cli("add", inputs=["2024-01-15", "expense", "food", "15000", "점심", "meal"])
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료] id=TX-000001", out)

    def test_add_reprompts_on_invalid_input(self) -> None:
        code, out, err = self.run_cli(
            "add",
            inputs=["2024-13-40", "2024-01-15", "refund", "expense", "nope", "food", "0", "-1", "abc", "1000", "", ""],
        )
        self.assertEqual(code, 0)
        self.assertIn("날짜 형식이 올바르지 않습니다", err)
        self.assertIn("[힌트] 예: 2024-01-15", err)
        self.assertIn("허용되지 않은 타입", err)
        self.assertIn("등록되지 않은 카테고리", err)
        self.assertIn("금액은 0보다 커야", err)
        self.assertIn("금액은 정수여야", err)
        self.assertIn("id=TX-000001", out)

    def test_list_is_latest_first_with_limit(self) -> None:
        self.add("2024-01-12", "expense", "transport", "20000")
        self.add("2024-01-15", "expense", "food", "15000")
        self.add("2024-01-14", "income", "salary", "3000000")
        self.add("2024-01-15", "expense", "rent", "150000")
        code, out, _ = self.run_cli("list", "--limit", "3")
        self.assertEqual(code, 0)
        self.assertEqual(self.tx_ids(out), ["TX-000004", "TX-000002", "TX-000003"])
        self.assertIn("전체 4건", out)

    def test_list_rejects_non_positive_limit(self) -> None:
        code, _, err = self.run_cli("list", "--limit", "0")
        self.assertNotEqual(code, 0)
        self.assertIn("[오류]", err)
        self.assertNotIn("Traceback", err)


class SearchTest(CliTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add("2024-01-10", "expense", "food", "12000", "점심 김밥", "meal")
        self.add("2024-01-20", "expense", "transport", "1450", "지하철")
        self.add("2024-02-01", "expense", "food", "9000", "점심", "Meal,cafe")
        self.add("2024-02-25", "income", "salary", "3000000", "월급")

    def test_period_filter(self) -> None:
        _, out, _ = self.run_cli("search", "--from", "2024-01-01", "--to", "2024-01-31")
        self.assertEqual(self.tx_ids(out), ["TX-000002", "TX-000001"])

    def test_keyword_tag_category_type(self) -> None:
        _, out, _ = self.run_cli("search", "--q", "점심", "--tag", "meal", "--category", "food", "--type", "expense")
        self.assertEqual(self.tx_ids(out), ["TX-000003", "TX-000001"])

    def test_invalid_range(self) -> None:
        code, _, err = self.run_cli("search", "--from", "2024-02-01", "--to", "2024-01-01")
        self.assertNotEqual(code, 0)
        self.assertIn("시작일", err)


class UpdateDeleteTest(CliTestCase):
    def test_update_changes_only_given_fields(self) -> None:
        tx_id = self.add("2024-01-15", "expense", "food", "15000", "점심", "meal")
        code, out, _ = self.run_cli("update", "--id", tx_id, "--amount", "18000", "--tags", "")
        self.assertEqual(code, 0)
        self.assertIn("수정 완료", out)
        record = json.loads((self.data_dir / "transactions.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(record["amount"], 18000)
        self.assertEqual(record["memo"], "점심")
        self.assertEqual(record["tags"], [])

    def test_update_and_delete_unknown_id(self) -> None:
        for argv in (("update", "--id", "TX-999999", "--amount", "1"), ("delete", "--id", "TX-999999")):
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 3)
            self.assertIn("없는 데이터", err)

    def test_delete_removes_and_ids_are_not_reused(self) -> None:
        first = self.add("2024-01-15", "expense", "food", "15000")
        code, _, _ = self.run_cli("delete", "--id", first)
        self.assertEqual(code, 0)
        _, out, _ = self.run_cli("list")
        self.assertEqual(self.tx_ids(out), [])
        self.assertEqual(self.add("2024-01-16", "expense", "food", "1000"), "TX-000002")
        self.assertEqual(list(self.data_dir.glob("*.tmp")), [])


class SummaryBudgetTest(CliTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add("2024-01-14", "income", "salary", "3000000")
        self.add("2024-01-03", "expense", "rent", "150000")
        self.add("2024-01-15", "expense", "food", "15000")
        self.add("2024-01-20", "expense", "food", "30000")
        self.add("2024-01-12", "expense", "transport", "20000")

    def test_summary_totals_and_top(self) -> None:
        code, out, _ = self.run_cli("summary", "--month", "2024-01", "--top", "2")
        self.assertEqual(code, 0)
        self.assertIn("총 수입: 3,000,000원", out)
        self.assertIn("총 지출: 215,000원", out)
        self.assertIn("잔액: 2,785,000원", out)
        self.assertRegex(out, r"1\) rent\s+150,000원")
        self.assertRegex(out, r"2\) food\s+45,000원")
        self.assertNotIn("3) transport", out)

    def test_summary_without_data(self) -> None:
        _, out, _ = self.run_cli("summary", "--month", "2023-12")
        self.assertIn("데이터 없음", out)

    def test_budget_usage_and_exceeded_warning(self) -> None:
        code, out, _ = self.run_cli("budget", "set", "--month", "2024-01", "--amount", "500000")
        self.assertEqual(code, 0)
        _, out, _ = self.run_cli("summary", "--month", "2024-01")
        self.assertIn("사용률 43.0%", out)
        self.run_cli("budget", "set", "--month", "2024-01", "--amount", "200000")
        _, out, _ = self.run_cli("summary", "--month", "2024-01")
        self.assertIn("[경고]", out)
        self.assertIn("15,000원 초과", out)
        budgets = (self.data_dir / "budgets.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(budgets), 1)


class CategoryTest(CliTestCase):
    def test_add_duplicate_and_remove_unused(self) -> None:
        self.assertEqual(self.run_cli("category", "add", inputs=["Coffee"])[0], 0)
        self.assertEqual(self.run_cli("category", "add", "--name", "coffee")[0], 4)
        self.assertEqual(self.run_cli("category", "remove", "--name", "coffee")[0], 0)

    def test_remove_in_use_requires_replacement(self) -> None:
        self.add("2024-01-15", "expense", "food", "15000")
        code, _, err = self.run_cli("category", "remove", "--name", "food", inputs=[""])
        self.assertNotEqual(code, 0)
        self.assertIn("취소", err)
        code, out, _ = self.run_cli("category", "remove", "--name", "food", "--replace", "etc")
        self.assertEqual(code, 0)
        self.assertIn("1건 -> etc", out)
        _, out, _ = self.run_cli("search", "--category", "etc")
        self.assertEqual(len(self.tx_ids(out)), 1)


class ImportExportTest(CliTestCase):
    def test_import_sample_then_export_round_trip(self) -> None:
        code, out, _ = self.run_cli("import", "--from", str(ROOT / "samples" / "import_sample.csv"))
        self.assertEqual(code, 0)
        self.assertIn("imported=5, skipped=0", out)

        out_csv = Path(self._tmp.name) / "export.csv"
        code, out, _ = self.run_cli("export", "--out", str(out_csv), "--month", "2024-01")
        self.assertEqual(code, 0)
        self.assertIn("(5 records)", out)
        with out_csv.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(list(rows[0].keys()), ["date", "type", "category", "amount", "memo", "tags"])
        self.assertIn({"date": "2024-01-10", "type": "expense", "category": "food", "amount": "12000",
                       "memo": "점심", "tags": "meal,lunch"}, rows)

    def test_import_skips_invalid_rows_with_reasons(self) -> None:
        code, out, _ = self.run_cli("import", "--from", str(ROOT / "samples" / "import_with_errors.csv"))
        self.assertEqual(code, 0)
        self.assertIn("imported=2, skipped=4", out)
        self.assertIn("3행 건너뜀", out)

    def test_export_requires_period(self) -> None:
        code, _, err = self.run_cli("export", "--out", str(Path(self._tmp.name) / "x.csv"))
        self.assertEqual(code, 2)
        self.assertIn("--month", err)

    def test_import_missing_file(self) -> None:
        code, _, err = self.run_cli("import", "--from", "no-such-file.csv")
        self.assertEqual(code, 3)
        self.assertIn("[힌트]", err)


class SafetyTest(CliTestCase):
    def test_corrupted_line_is_reported_without_traceback(self) -> None:
        self.add("2024-01-15", "expense", "food", "15000")
        with (self.data_dir / "transactions.jsonl").open("a", encoding="utf-8") as fh:
            fh.write('{"id": "TX-000002", broken\n')
        code, _, err = self.run_cli("list")
        self.assertEqual(code, 5)
        self.assertIn("2번째 줄", err)
        self.assertNotIn("Traceback", err)

    def test_backup_and_restore(self) -> None:
        self.add("2024-01-15", "expense", "food", "15000")
        self.assertEqual(self.run_cli("backup", "create")[0], 0)
        name = next((self.data_dir / "backups").iterdir()).name
        self.run_cli("delete", "--id", "TX-000001")
        code, out, _ = self.run_cli("backup", "restore", "--name", name, "--yes")
        self.assertEqual(code, 0)
        _, out, _ = self.run_cli("list")
        self.assertEqual(self.tx_ids(out), ["TX-000001"])

    def test_recurring_apply_is_idempotent_and_clamps_month_end(self) -> None:
        self.run_cli("recurring", "add", inputs=["31", "expense", "rent", "500000", "월세", ""])
        code, out, _ = self.run_cli("recurring", "apply", "--month", "2024-02")
        self.assertEqual(code, 0)
        self.assertIn("2024-02-29", out)
        _, out, _ = self.run_cli("recurring", "apply", "--month", "2024-02")
        self.assertIn("created=0, skipped=1", out)


if __name__ == "__main__":
    unittest.main()
