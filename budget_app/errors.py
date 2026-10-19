"""애플리케이션 전용 예외.

모든 예외는 사용자에게 보여줄 '원인(message)'과 '해결 힌트(hint)'를 함께 가진다.
CLI 계층의 예외 처리 데코레이터가 이 정보를 이용해 스택트레이스 대신
읽기 쉬운 오류 메시지를 출력하고 0이 아닌 종료 코드를 반환한다.
"""

from __future__ import annotations


class AppError(Exception):
    """사용자에게 안내 가능한 모든 오류의 기반 클래스."""

    exit_code: int = 1

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class ValidationError(AppError):
    """사용자 입력 값이 형식/범위 규칙을 만족하지 않을 때."""

    exit_code = 2


class NotFoundError(AppError):
    """요청한 거래/카테고리/예산 등이 존재하지 않을 때."""

    exit_code = 3


class ConflictError(AppError):
    """중복 등록, 사용 중인 카테고리 삭제 등 현재 상태와 충돌할 때."""

    exit_code = 4


class StorageError(AppError):
    """저장 파일을 읽거나 쓸 수 없을 때(손상, 권한 문제 등)."""

    exit_code = 5
