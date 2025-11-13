from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import date

class Job(BaseModel):
    job_title: str
    company_name: str
    job_location: str

    # ⚠️ 전부 Optional[...] 로 변경 (파이프 사용 금지)
    is_remote_friendly: Optional[bool] = None
    employment_type: Optional[str] = None
    compensation: Optional[str] = None

    # URL은 LLM이 비울 수 있으므로 Optional로 완화 + validator에서 정제
    job_posting_url: Optional[str] = None

    job_summary: str

    key_qualifications: Optional[List[str]] = None
    job_responsibilities: Optional[List[str]] = None
    date_listed: Optional[date] = None
    required_technologies: Optional[List[str]] = None
    core_keywords: Optional[List[str]] = None

    role_seniority_level: Optional[str] = None
    years_of_experience_required: Optional[str] = None
    minimum_education: Optional[str] = None
    job_benefits: Optional[List[str]] = None
    includes_equity: Optional[bool] = None
    offers_visa_sponsorship: Optional[bool] = None
    hiring_company_size: Optional[str] = None
    hiring_industry: Optional[str] = None
    source_listing_url: Optional[str] = None
    full_raw_job_description: Optional[str] = None

    # --- 정제용 validator들 ---

    @field_validator(
        "job_posting_url", "source_listing_url",
        mode="before"
    )
    def _normalize_urls(cls, v):
        # None, 빈 문자열, 공백만 있는 문자열 -> None으로 통일
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @field_validator(
        "key_qualifications", "job_responsibilities",
        "required_technologies", "core_keywords", "job_benefits",
        mode="before"
    )
    def _normalize_list_fields(cls, v):
        # 빈 문자열/None/빈 리스트를 전부 None으로 통일
        if v in (None, "", []):
            return None
        # 단일 문자열이 오면 리스트로 감싸기
        if isinstance(v, str):
            v = [v]
        # 리스트 내 공백 제거 및 빈 항목 필터
        if isinstance(v, list):
            cleaned = [str(x).strip() for x in v if str(x).strip()]
            return cleaned or None
        return v


class JobList(BaseModel):
    jobs: List[Job]


class RankedJob(BaseModel):
    job: Job
    match_score: int
    reason: str


class RankedJobList(BaseModel):
    ranked_jobs: List[RankedJob]


class ChosenJob(BaseModel):
    job: Job
    selected: bool
    reason: str
