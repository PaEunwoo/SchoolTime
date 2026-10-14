import asyncio
from typing import Any

import aiohttp


BASE_URL = "https://open.neis.go.kr/hub/"
ENDPOINTS = {
    "school": "schoolInfo",
    "elementary": "elsTimetable",
    "middle": "misTimetable",
    "high": "hisTimetable",
    "schedule": "SchoolSchedule",
}
MAX_RESULTS = 1000
PAGE_SIZE = 100


class NeisError(Exception):
    """Base error for NEIS API failures."""


class NeisAuthenticationError(NeisError):
    pass


class NeisConnectionError(NeisError):
    pass


class NeisResponseError(NeisError):
    pass


class NeisResultLimitError(NeisError):
    pass


class NeisClient:
    def __init__(
        self,
        api_key: str,
        session: aiohttp.ClientSession | None = None,
        timeout_seconds: float = 12,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self._session = session
        self._owns_session = session is None
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.retries = retries

    async def start(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def _request_page(
        self, endpoint: str, params: dict[str, Any], page: int, page_size: int
    ) -> tuple[list[dict[str, Any]], int | None]:
        if self._session is None:
            raise RuntimeError("NEIS 클라이언트가 시작되지 않았습니다.")

        request_params = {
            **params,
            "KEY": self.api_key,
            "Type": "json",
            "pIndex": page,
            "pSize": page_size,
        }
        url = BASE_URL + endpoint
        for attempt in range(self.retries + 1):
            try:
                async with self._session.get(
                    url, params=request_params, timeout=self.timeout
                ) as response:
                    if response.status >= 500:
                        if attempt < self.retries:
                            await asyncio.sleep(0.25 * (2**attempt))
                            continue
                        raise NeisConnectionError(
                            "나이스 API 서버가 일시적으로 응답하지 않습니다."
                        )
                    if response.status >= 400:
                        raise NeisResponseError(
                            f"나이스 API 요청이 거부되었습니다 (HTTP {response.status})."
                        )
                    try:
                        payload = await response.json(content_type=None)
                    except (ValueError, aiohttp.ContentTypeError) as exc:
                        raise NeisResponseError(
                            "나이스 API에서 올바르지 않은 응답을 받았습니다."
                        ) from exc
                rows, total = self._parse_payload(payload, endpoint)
                return rows, total
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt < self.retries:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise NeisConnectionError(
                    "나이스 API에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
                ) from exc
        raise NeisConnectionError("나이스 API 요청을 완료하지 못했습니다.")

    @staticmethod
    def _parse_payload(
        payload: Any, endpoint: str
    ) -> tuple[list[dict[str, Any]], int | None]:
        if not isinstance(payload, dict):
            raise NeisResponseError("나이스 API 응답 형식이 올바르지 않습니다.")
        blocks = payload.get(endpoint)
        if not isinstance(blocks, list):
            raise NeisResponseError("나이스 API 응답에 결과 항목이 없습니다.")

        total: int | None = None
        rows: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            for head in block.get("head", []):
                if not isinstance(head, dict):
                    continue
                result = head.get("RESULT")
                if isinstance(result, dict):
                    code = str(result.get("CODE", ""))
                    message = str(result.get("MESSAGE", ""))
                    if code == "INFO-200":
                        return [], 0
                    if code and code != "INFO-000":
                        if code in {"ERROR-290", "ERROR-291", "ERROR-292"}:
                            raise NeisAuthenticationError(
                                "나이스 인증키가 유효하지 않거나 해당 API 사용 권한이 없습니다."
                            )
                        raise NeisResponseError(
                            f"나이스 API 오류 ({code}): {message or '요청을 처리할 수 없습니다.'}"
                        )
                if "list_total_count" in head:
                    try:
                        total = int(head["list_total_count"])
                    except (TypeError, ValueError):
                        raise NeisResponseError(
                            "나이스 API가 올바르지 않은 전체 건수를 반환했습니다."
                        )
            block_rows = block.get("row", [])
            if isinstance(block_rows, list):
                rows.extend(row for row in block_rows if isinstance(row, dict))
        return rows, total

    async def fetch_all(
        self, endpoint_name: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        endpoint = ENDPOINTS[endpoint_name]
        query = dict(params or {})
        first_rows, total = await self._request_page(
            endpoint, query, page=1, page_size=PAGE_SIZE
        )
        if total is not None and total > MAX_RESULTS:
            raise NeisResultLimitError(
                f"조회 결과가 {MAX_RESULTS}건을 초과합니다. 검색 조건을 더 구체적으로 입력해 주세요."
            )
        rows = list(first_rows)
        if total is None:
            if len(rows) >= MAX_RESULTS:
                raise NeisResultLimitError(
                    f"조회 결과가 {MAX_RESULTS}건을 초과할 수 있어 표시를 중단했습니다."
                )
            return rows

        page = 2
        while len(rows) < total and len(rows) < MAX_RESULTS:
            next_rows, _ = await self._request_page(
                endpoint, query, page=page, page_size=PAGE_SIZE
            )
            if not next_rows:
                break
            rows.extend(next_rows)
            page += 1
        if len(rows) > MAX_RESULTS:
            raise NeisResultLimitError(
                f"조회 결과가 {MAX_RESULTS}건을 초과합니다. 검색 조건을 더 구체적으로 입력해 주세요."
            )
        return rows

    async def search_schools(self, school_name: str) -> list[dict[str, Any]]:
        return await self.fetch_all("school", {"SCHUL_NM": school_name.strip()})

    async def get_timetable(
        self,
        school_type: str,
        office_code: str,
        school_code: str,
        grade: int,
        class_num: int,
        day: str,
    ) -> list[dict[str, Any]]:
        kind = school_type.strip()
        if "초등" in kind:
            endpoint_name = "elementary"
        elif "중" in kind:
            endpoint_name = "middle"
        elif "고" in kind:
            endpoint_name = "high"
        else:
            raise NeisResponseError(f"지원하지 않는 학교급입니다: {school_type}")
        return await self.fetch_all(
            endpoint_name,
            {
                "ATPT_OFCDC_SC_CODE": office_code,
                "SD_SCHUL_CODE": school_code,
                "ALL_TI_YMD": day.replace("-", ""),
                "GRADE": str(grade),
                "CLASS_NM": str(class_num),
            },
        )

    async def get_schedule(
        self, office_code: str, school_code: str, start_day: str, end_day: str
    ) -> list[dict[str, Any]]:
        return await self.fetch_all(
            "schedule",
            {
                "ATPT_OFCDC_SC_CODE": office_code,
                "SD_SCHUL_CODE": school_code,
                "AA_FROM_YMD": start_day.replace("-", ""),
                "AA_TO_YMD": end_day.replace("-", ""),
            },
        )
