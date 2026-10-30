# backend/app/schemas/ai.py
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Literal, Union

class GoalProgressBarWidget(BaseModel):
    """Виджет прогресса финансовой цели (например, 'Подушка безопасности')."""
    type: Literal["goal_progress"] = "goal_progress"
    title: str = Field(..., description="Название цели")
    current_amount: float = Field(..., description="Текущие накопления")
    target_amount: float = Field(..., description="Целевая сумма")
    recommendation: str = Field(..., description="Короткий практический совет по ускорению накопления")

class CategoryLimitWidget(BaseModel):
    """Виджет рекомендуемого лимита по проблемной категории трат."""
    type: Literal["category_limit"] = "category_limit"
    category: str = Field(..., description="Название категории")
    spent_amount: float = Field(..., description="Фактически потрачено за месяц")
    recommended_limit: float = Field(..., description="Рекомендуемый ИИ лимит на месяц")
    severity: Literal["warning", "critical", "normal"] = Field("normal", description="Степень превышения лимита")


class Recommendation(BaseModel):
    id: str
    title: str
    observation: str
    action: str
    priority: Literal["normal", "warning"] = "normal"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class AdvisorChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    start_date: date
    end_date: date
    message: str = Field(default="Разбери мой бюджет и дай рекомендации", min_length=1, max_length=1500)
    history: List[ChatMessage] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_dates(self):
        if not date(2000, 1, 1) <= self.start_date <= self.end_date <= date(2100, 12, 31):
            raise ValueError("Выберите период с 2000 по 2100 год: начало не позже окончания")
        return self


class AIAdvisorResponse(BaseModel):
    """Гибридный ответ эндпоинта ИИ-ассистента."""
    year: int
    month: int
    markdown_insights: str = Field(..., description="Персонализированный текстовый отчет в формате Markdown")
    widgets: List[Union[GoalProgressBarWidget, CategoryLimitWidget]] = Field(
        default_factory=list, 
        description="Структурированный массив виджетов для рендера в UI"
    )
    start_date: date
    end_date: date
    recommendations: List[Recommendation] = Field(default_factory=list)
    source: Literal["gemini", "rules", "empty"] = "rules"
