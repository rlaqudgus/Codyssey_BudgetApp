# 콘솔 가계부 (budget_app)

파일 기반(JSONL)으로 수입/지출을 관리하는 Python 콘솔 가계부입니다.
기능 수보다 **예외 상황에서도 데이터가 안전한 것**을 목표로 설계했습니다.

- 거래 추가/목록/검색/수정/삭제, 월별 요약, 예산 경고, 카테고리 관리, CSV 가져오기/내보내기
- 보너스: 백업/복구, 반복 거래, 한글 폭을 고려한 표 정렬, 임시 파일 + rename 원자적 저장
- **표준 라이브러리만 사용** (pip install 불필요), Python 3.10 이상

> 학습 목표(파일 저장, 계층 구조, 제너레이터, 데코레이터, 타입 힌트)별 설명 자료: [docs/STUDY_GUIDE.md](docs/STUDY_GUIDE.md)

---

## 1. 실행 방법

```bash
# 프로젝트 루트에서
python -m budget_app --help              # 전체 명령 목록
python -m budget_app <command> --help    # 명령별 사용법
python -m budget_app add                 # 예: 거래 추가(대화형)
```

공통 옵션(명령 앞/뒤 어디에 써도 됨)

| 옵션 | 설명 |
| --- | --- |
| `--data-dir PATH` | 저장 폴더 (기본 `./data`) |
| `--verbose` | 실행 로그·실행 시간을 콘솔(stderr)에도 출력 |
| `--help` | 사용법 출력 |

테스트 실행

```bash
python -m unittest discover -s tests -v
```

> Windows에서 출력을 파일로 리다이렉트할 때 한글이 깨지면 `set PYTHONUTF8=1` 후 실행하세요.

---

## 2. 저장 파일 위치와 형식

기본 위치는 `./data` 이며 `--data-dir` 로 바꿀 수 있습니다. 포맷은 **JSONL**(한 줄 = JSON 객체 1개, UTF-8)입니다.

| 파일 | 내용 | 예시 한 줄 |
| --- | --- | --- |
| `transactions.jsonl` | 거래 내역 | `{"id": "TX-000001", "type": "expense", "date": "2024-01-15", "amount": 15000, "category": "food", "memo": "점심", "tags": ["meal"]}` |
| `categories.jsonl` | 카테고리 | `{"name": "food"}` |
| `budgets.jsonl` | 월 예산 | `{"month": "2024-01", "amount": 500000}` |
| `recurring.jsonl` | 반복 거래 규칙(보너스) | `{"id": "RC-001", "day": 25, "type": "income", "amount": 3000000, "category": "salary", "memo": "월급", "tags": []}` |
| `transactions.seq` | 마지막 발급 거래 번호(삭제된 id 재사용 방지) | `{"last": 12}` |
| `app.log` | 실행 로그(데코레이터가 기록, 스택트레이스는 여기에만) | |
| `backups/<YYYYMMDD-HHMMSS>/` | 백업 폴더(보너스) | |

**거래(Transaction) 필드**: `id`(유일, `TX-000001`), `type`(`income`/`expense`), `date`(`YYYY-MM-DD`), `amount`(양의 정수), `category`(등록된 카테고리), `memo`(선택), `tags`(선택, 문자열 배열). 반복 규칙으로 생성된 거래에는 `source`(`RC-001@2024-02`)가 추가됩니다.

### 초기 실행 정책

- 저장 파일이 없으면 **자동 생성**하고 `[안내]` 메시지를 출력합니다.
- 카테고리 파일이 비어 있으면 **(안 A) 기본 카테고리를 자동 생성**합니다: `food, transport, rent, shopping, salary, etc`

---

## 3. 주요 명령 예시

### add — 거래 추가 (대화형)

```text
$ python -m budget_app add
날짜(YYYY-MM-DD, 엔터=오늘): 2024-13-40
[오류] 날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): '2024-13-40'
[힌트] 예: 2024-01-15
날짜(YYYY-MM-DD, 엔터=오늘): 2024-01-15
타입(income/expense): expense
카테고리 [food, transport, rent, shopping, salary, etc]: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001
```

- 잘못된 입력(날짜 형식, 0/음수/문자 금액, 허용되지 않은 type, 미등록 카테고리)은 원인+힌트를 보여주고 **같은 항목을 다시 묻습니다.**
- 금액은 `15,000`처럼 천 단위 쉼표를 써도 됩니다. 타입은 `수입`/`지출`도 허용합니다.
- 지출 추가 후 해당 월 예산을 넘으면 즉시 `[경고]`를 출력합니다.

### list — 최신순 목록 (스트리밍)

```text
$ python -m budget_app list --limit 3
ID        | 날짜       | 타입    | 카테고리 |      금액 | 메모     | 태그
----------+------------+---------+----------+-----------+----------+------
TX-000002 | 2024-01-25 | income  | salary   | 3,000,000 | 1월 급여 |
TX-000006 | 2024-01-18 | expense | shopping |    45,000 | 운동화   |
TX-000001 | 2024-01-15 | expense | food     |    15,000 | 점심     | #meal
(최신 3건 / 전체 6건)
```

`--limit N` (기본 10). 날짜 내림차순, 같은 날짜는 나중에 등록한 거래가 먼저입니다.

### search — 조건 검색 (최신순, 스트리밍)

```bash
python -m budget_app search --from 2024-01-01 --to 2024-01-31
python -m budget_app search --category food --type expense
python -m budget_app search --q 점심 --tag meal --limit 5
python -m budget_app search --month 2024-01
```

| 옵션 | 의미 |
| --- | --- |
| `--from` / `--to` | 기간(양 끝 포함) |
| `--month` | 해당 월 |
| `--category` | 카테고리 |
| `--type` | `income` / `expense` |
| `--q` | 메모 키워드(부분 일치, 대소문자 무시) |
| `--tag` | 태그(정확히 일치, 대소문자 무시) |
| `--limit` | 최대 출력 건수 |

조건은 모두 AND로 결합됩니다.

### update — 거래 수정 (**옵션 방식, 안 A로 고정**)

```bash
python -m budget_app update --id TX-000001 --amount 18000
python -m budget_app update --id TX-000001 --category food --memo "팀 점심" --tags "meal,team"
python -m budget_app update --id TX-000001 --tags ""        # 태그 비우기
```

지정한 필드(`--date --type --category --amount --memo --tags`)만 바뀌며 수정 전/후를 출력합니다.
없는 id는 `[오류] id=... 거래가 없습니다 (없는 데이터).` 와 종료 코드 3을 반환합니다.

### delete — 거래 삭제

```bash
python -m budget_app delete --id TX-000001
```

### summary — 월별 요약 + 예산

```text
$ python -m budget_app budget set --month 2024-01 --amount 600000
[저장 완료] 2024-01 예산 600,000원

$ python -m budget_app summary --month 2024-01 --top 3
=== 2024-01 요약 ===
총 수입: 3,000,000원
총 지출: 573,450원
잔액: 2,426,550원
예산: 600,000원 (사용률 95.6%)
[주의] 예산의 95.6%를 사용했습니다. 남은 예산 26,550원

지출 TOP 3
1) rent      500,000원
2) shopping   45,000원
3) food       27,000원
```

- 예산 초과 시: `[경고] 2024-01 예산을 15,000원 초과했습니다!`
- 거래가 없는 달: `[데이터 없음] 2024-03 에 해당하는 거래가 없습니다.`

### budget — 월 예산

```bash
python -m budget_app budget set --month 2024-01 --amount 500000   # 같은 달은 덮어쓰기
python -m budget_app budget show --month 2024-01                  # 지출/사용률/초과 여부
python -m budget_app budget list
```

### category — 카테고리 관리

```text
$ python -m budget_app category add
카테고리명: coffee
[저장 완료] category=coffee

$ python -m budget_app category list
- food       (사용 3건)
- transport  (사용 1건)
...

$ python -m budget_app category remove --name food
[안내] 'food' 카테고리를 사용하는 거래/반복 규칙이 3건 있습니다.
거래를 옮길 대체 카테고리 (취소하려면 엔터):
[오류] 카테고리 삭제를 취소했습니다.
[힌트] category remove --name food --replace <대체카테고리> 로 다시 실행하세요.

$ python -m budget_app category remove --name food --replace etc
[완료] category=food 삭제 (3건 -> etc 로 이동)
```

- 카테고리명은 소문자로 정규화되며 공백/쉼표는 쓸 수 없습니다(한글 가능).
- **사용 중인 카테고리 삭제 정책**: 대체 카테고리를 요구합니다. `--replace`가 없으면 대화형으로 대체 카테고리를 묻고, 빈 입력이면 삭제를 취소합니다. 대체 시 해당 거래와 반복 규칙을 원자적으로 일괄 이동합니다.

### import / export — CSV

```text
$ python -m budget_app export --out export.csv --month 2024-01
[완료] export.csv (6 records)

$ python -m budget_app export --out q1.csv --from 2024-01-01 --to 2024-03-31 --type expense

$ python -m budget_app import --from samples/import_sample.csv
[안내] 등록된 id: TX-000002 ~ TX-000006
[완료] imported=5, skipped=0

$ python -m budget_app import --from samples/import_with_errors.csv
[경고] 3행 건너뜀: 날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): '2024-02-30'
[경고] 4행 건너뜀: 금액은 0보다 커야 합니다: '-500'
[경고] 5행 건너뜀: 허용되지 않은 타입입니다: 'refund'
[경고] 6행 건너뜀: 등록되지 않은 카테고리 'coffee'
[완료] imported=2, skipped=4
```

- `export`는 `--month` 또는 `--from`/`--to` 중 **하나 이상의 기간 조건이 필수**입니다(추가로 `--category`, `--type` 사용 가능).
- `import`는 잘못된 행을 줄 번호·사유와 함께 건너뛰고, 나머지를 한 번에 원자적으로 저장합니다.
  `--create-categories`를 주면 미등록 카테고리를 자동 등록합니다.

### backup — 백업/복구 (보너스)

```bash
python -m budget_app backup create                          # data/backups/20240131-235959/
python -m budget_app backup list
python -m budget_app backup restore --name 20240131-235959 --yes
```

복구 전 현재 상태를 `...-before-restore` 백업으로 자동 보관합니다.

### recurring — 반복 거래 (보너스)

```bash
python -m budget_app recurring add                 # 대화형: 매월 날짜(1~31)/타입/카테고리/금액/메모/태그
python -m budget_app recurring list
python -m budget_app recurring apply --month 2024-02
python -m budget_app recurring remove --id RC-001
```

- 해당 월에 없는 날짜(예: 31일 → 2월)는 말일로 생성합니다.
- 같은 달에 여러 번 `apply` 해도 이미 생성된 규칙은 건너뜁니다(중복 생성 방지).

---

## 4. import / export CSV 스키마

UTF-8, **헤더 포함**. 컬럼 순서와 이름은 아래로 고정합니다(import 시 헤더 대소문자/공백은 무시, BOM 허용).

| column | required | 설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` / `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양의 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표(`,`) 구분 문자열 — CSV 규칙상 따옴표로 감쌉니다. 예: `"meal,lunch"` |

```csv
date,type,category,amount,memo,tags
2024-01-25,income,salary,3000000,1월 급여,
2024-01-10,expense,food,12000,점심,"meal,lunch"
```

샘플: [`samples/import_sample.csv`](samples/import_sample.csv), [`samples/import_with_errors.csv`](samples/import_with_errors.csv)

> 엑셀에서 편집했다면 "CSV UTF-8(쉼표로 분리)" 형식으로 저장하세요.

---

## 5. 오류 처리와 종료 코드

모든 오류는 스택트레이스 대신 **원인 + 해결 힌트**로 출력합니다(stderr).

```text
[오류] id=TX-000099 거래가 없습니다 (없는 데이터).
[힌트] 'list' 또는 'search' 로 정확한 거래 id를 확인하세요. 예: TX-000012
```

| 종료 코드 | 의미 |
| --- | --- |
| 0 | 정상 종료 |
| 1 | 일반 오류(입력 취소, 파일 I/O, 예상하지 못한 오류) |
| 2 | 입력/인자 검증 오류 |
| 3 | 대상 없음(없는 id, 없는 카테고리/파일/백업) |
| 4 | 충돌(중복 카테고리, 사용 중인 카테고리 삭제) |
| 5 | 저장 파일 손상/데이터 경로 오류(손상된 줄 번호 표시) |
| 130 | Ctrl+C 로 중단 |

---

## 6. 구조와 설계

```text
budget_app/
├── __main__.py            # python -m budget_app 진입점
├── models.py              # [모델] Transaction, NewTransaction, TransactionPatch, Budget, RecurringRule (dataclass)
├── validators.py          # 입력 문자열 -> 도메인 값 검증(대화형/옵션/CSV 공용)
├── query.py               # SearchCriteria: 검색 조건 + 필터 제너레이터
├── errors.py              # AppError(message, hint) 계층과 종료 코드
├── decorators.py          # handle_errors / log_execution / timed
├── formatting.py          # 한글 폭을 고려한 표 정렬(외부 라이브러리 없음)
├── console.py             # [오류]/[힌트]/[안내]/[완료] 출력 규칙
├── context.py             # 저장소·서비스 조립(Composition Root), 데이터 폴더 초기화
├── storage/               # [저장소] 파일 I/O만 담당
│   ├── atomic.py          #   임시 파일 -> fsync -> os.replace
│   ├── jsonl.py           #   JsonlFile: stream(yield) / append / rewrite
│   ├── transactions.py    #   TransactionRepository
│   ├── categories.py      #   CategoryStore
│   ├── budgets.py         #   BudgetStore
│   └── recurring.py       #   RecurringStore
├── services/              # [서비스] 비즈니스 규칙(콘솔을 모름)
│   ├── transaction_service.py, category_service.py, budget_service.py
│   ├── report_service.py, csv_service.py, backup_service.py, recurring_service.py
└── cli/                   # [CLI] 인자 파싱, 대화형 입력, 출력
    ├── app.py             #   파서 구성, 로깅 설정, 데코레이터가 적용된 디스패처
    ├── base.py            #   공통 옵션, 인자 타입 변환기, 한글 오류 파서
    ├── prompts.py         #   검증 실패 시 재입력
    ├── views.py           #   거래 표/예산 상태 출력
    └── commands/          #   명령별 모듈(add, listing, search, update, delete, summary, budget, transfer, category, recurring, backup)
```

**계층별 책임**: CLI는 입력을 받아 서비스 호출 결과를 출력만 하고, 서비스는 규칙(카테고리 존재 여부, 예산 계산, 중복 방지)을 판단하며, 저장소는 파일 읽기/쓰기만 합니다. 덕분에 서비스는 콘솔 없이 단위 테스트할 수 있고, 저장 포맷을 바꿔도 저장소 계층만 수정하면 됩니다.

### 제너레이터 스트리밍

`JsonlFile.stream()`은 파일을 한 줄씩 읽어 `yield`합니다. 파일 전체를 리스트로 만들지 않으므로 거래가 수십만 건이어도 메모리는 한 줄 분량만 씁니다.

- `list --limit N`: 스트림을 한 번 순회하며 `heapq.nlargest(N, ...)`로 **상위 N건만 유지**(메모리 O(N)).
- `search`: `SearchCriteria.filter()` 제너레이터로 조건에 맞는 거래만 흘려보낸 뒤 정렬합니다.
- `summary`: 거래를 쌓지 않고 합계/카테고리별 Counter만 누적합니다.
- `update/delete/import`: 원본을 스트리밍으로 읽으며 임시 파일에 바로 씁니다.

### 데코레이터로 공통 관심사 분리

```python
@handle_errors      # AppError -> [오류]/[힌트] + 종료 코드, 그 외 예외는 요약만 출력(스택트레이스는 app.log)
@log_execution      # 시작/종료/실패 로그
@timed              # 실행 시간 로그
def run_command(args: argparse.Namespace) -> int: ...
```

명령 함수에는 try/except·로그·시간 측정 코드가 없습니다. `@timed`는 `JsonlFile.rewrite`, `ReportService.monthly_summary`, CSV 입출력, 백업에도 재사용됩니다(`--verbose`로 확인).

### 타입 힌트로 계약 명시

```python
def latest_first(stream: Iterable[Transaction], limit: int | None) -> ListResult: ...
def parse_amount(raw: str | int) -> int: ...                       # 실패 시 ValidationError
def update(self, tx_id: str, patch: TransactionPatch) -> tuple[Transaction, Transaction]: ...
def handle_errors(func: Callable[P, int]) -> Callable[P, int]: ...  # ParamSpec 으로 원래 시그니처 보존
```

`TransactionPatch`의 각 필드는 `X | None`이라 "None = 변경 안 함"이라는 의미가 타입에 드러나고,
`Transaction`은 `frozen=True`라 수정 시 반드시 새 객체를 만들어(`dataclasses.replace`) 저장소에 넘겨야 합니다.

### 저장 안정성(원자성)

- `update/delete/import/카테고리 대체/예산 설정`은 **같은 폴더의 임시 파일에 전부 쓴 뒤 `fsync` → `os.replace`** 로 교체합니다. 중간에 오류·전원 차단이 나도 원본은 이전 상태 그대로 남고 임시 파일은 삭제됩니다.
- `add`는 파일 끝에 한 줄만 추가(append + fsync)합니다.
- 손상된 줄이 있으면 파일명과 줄 번호, 복구 방법(`backup restore`)을 안내합니다.
