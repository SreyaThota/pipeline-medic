from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    log_text: str = Field(
        min_length=1,
        description="Raw CI log text. Must contain non-whitespace characters.",
        examples=["FAILED tests/test_api.py::test_login - AssertionError"],
    )


class DiagnoseResponse(BaseModel):
    summary: str
    model: str
