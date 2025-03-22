from pydantic import BaseModel, Field, field_validator


class BacktestRequestSchema(BaseModel):
    start_year: int = Field(...)
    start_month: int = Field(..., ge=1,le=12)
    trade_day: int = Field(..., ge=1, le=31)
    weight_months: int = Field(...)
    initial_balance: int = Field(gt=0, default = 100000)
    fee_rate: float = Field(lt=0.1, default=0.001)

    @field_validator("initial_balance")
    @classmethod
    def balance_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError(f"초기 투자금액은 0보다 커야 합니다. 입력 : {v}")
        return v

    @field_validator("start_month")
    @classmethod
    def month_range_check(cls, v):
        if v < 1 or v > 12:
            raise ValueError(f"시작 월은 1부터 12 사이여야 합니다. 입력 : {v}")
        return v

    @field_validator("trade_day")
    @classmethod
    def trade_day_range_check(cls, v):
        if v < 1 or v > 31:
            raise ValueError(f"매매일은 1일부터 31일 사이여야 합니다. 입력 : {v}")
        return v

    @field_validator("fee_rate")
    @classmethod
    def fee_rate_limit(cls, v):
        if v > 0.1 or v < 0:
            raise ValueError("수수료율은 0% 이상이며 10%를 초과할 수 없습니다.")
        return v

    
    
