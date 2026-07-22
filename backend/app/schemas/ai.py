# backend/app/schemas/ai.py
from pydantic import BaseModel, Field
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

class AIAdvisorResponse(BaseModel):
    """Гибридный ответ эндпоинта ИИ-ассистента."""
    year: int
    month: int
    markdown_insights: str = Field(..., description="Персонализированный текстовый отчет в формате Markdown")
    widgets: List[Union[GoalProgressBarWidget, CategoryLimitWidget]] = Field(
        default_factory=list, 
        description="Структурированный массив виджетов для рендера в UI"
    )