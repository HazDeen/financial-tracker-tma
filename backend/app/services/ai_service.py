# backend/app/services/ai_service.py
import json
import re
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
from google.genai import types

from app.core.config import settings
from app.services.analytics_service import AnalyticsService
from app.schemas.ai import AIAdvisorResponse, GoalProgressBarWidget, CategoryLimitWidget

SYSTEM_INSTRUCTION = """
Ты — элитный финансовый аналитик и архитектурный ИИ-ассистент, встроенный в Telegram Mini App.
Твоя задача — проанализировать финансовый срез пользователя за месяц и выдать строгий гибридный ответ.

ТВОЙ ОТВЕТ ДОЛЖЕН СОСТОЯТЬ ИЗ ДВУХ БЛОКОВ, РАЗДЕЛЕННЫХ СТРОГОЙ МЕТКОЙ: `===JSON_WIDGETS===`

ЧАСТЬ 1: Текстовые инсайты (Markdown)
- Будь лаконичным, объективным и конкретным. Никакой воды и общих фраз.
- Проанализируй аномалии в тратах и структуру доходов.
- Дай 2-3 практических совета по сокращению расходов в топ-категориях.
- Оцени прогресс по чистой прибыли.
- Используй жирный шрифт, списки и эмодзи для удобного чтения в Telegram.

--- СТРОГИЙ РАЗДЕЛИТЕЛЬ ---
===JSON_WIDGETS===
--- СТРОГИЙ РАЗДЕЛИТЕЛЬ ---

ЧАСТЬ 2: Структурированные данные (строго валидный JSON)
После разделителя выведи ВАЛИДНЫЙ JSON-объект с ключом "widgets", содержащий массив рекомендаций:
{
  "widgets": [
    {
      "type": "category_limit",
      "category": "Название категории из отчета",
      "spent_amount": 15000.0,
      "recommended_limit": 10000.0,
      "severity": "warning"
    },
    {
      "type": "goal_progress",
      "title": "Подушка безопасности",
      "current_amount": 30000.0,
      "target_amount": 100000.0,
      "recommendation": "Откладывайте по 10% от чистой прибыли каждого месяца"
    }
  ]
}
Поле severity может принимать только значения: "normal", "warning", "critical".
ЗАПРЕЩЕНО выводить любой текст или символы оформления кода (```json) после разделителя ===JSON_WIDGETS===. ТОЛЬКО СЫРОЙ JSON.
"""

class AIAdvisorService:
    @staticmethod
    async def get_monthly_advice(db: AsyncSession, user_id: int, year: int, month: int) -> AIAdvisorResponse:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=503, 
                detail="В файле .env не задан GEMINI_API_KEY. Работа ИИ-аналитика невозможна."
            )

        # 1. Получаем финансовый срез из нашей аналитики
        report = await AnalyticsService.get_monthly_report(db, user_id, year, month)
        report_data = report.model_dump(mode="json")

        if report.total_income == 0 and report.total_expense == 0:
            return AIAdvisorResponse(
                year=year,
                month=month,
                markdown_insights="### 📊 Данных недостаточно\nЗа выбранный месяц нет транзакций. Загрузите выписку или добавьте смены, чтобы я смог провести анализ и рассчитать лимиты!",
                widgets=[]
            )

        # 2. Инициализируем клиент Gemini и отправляем промпт
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = f"Финансовый срез за месяц:\n{json.dumps(report_data, ensure_ascii=False, indent=2)}"

        try:
            # ИСПОЛЬЗУЕМ МОДЕЛЬ FLASH ДЛЯ ВЫСОКОЙ СКОРОСТИ И БОЛЬШОГО FREE-ЛИМИТА
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                )
            )
            raw_text = response.text or ""
            
        except Exception as e:
            # GRACEFUL DEGRADATION: Если API недоступен или квота исчерпана,
            # возвращаем базовую аналитику без падения сервера, чтобы UI работал стабильно.
            print(f"[AI Advisor Error] Сбой LLM API: {e}. Переключение на Fallback-аналитику.")
            
            fallback_markdown = (
                f"### ⚡ Автоматическая сводка за {month:02d}.{year}\n\n"
                f"* **Доход:** `{report.total_income:,.2f} ₽`\n"
                f"* **Расходы:** `{report.total_expense:,.2f} ₽`\n"
                f"* **Чистая прибыль:** `{report.net_profit:,.2f} ₽`\n\n"
                f"> *⚠️ Внешний нейросетевой консультант временно недоступен (превышен лимит запросов API). Пожалуйста, повторите попытку через 1 минуту для получения глубоких инсайтов.*"
            )
            
            # Генерация базового виджета лимита на основе Топ-1 категории трат
            fallback_widgets = []
            if report.top_expense_categories:
                top_cat = report.top_expense_categories[0]
                fallback_widgets.append(
                    CategoryLimitWidget(
                        category=top_cat.category,
                        spent_amount=float(top_cat.amount),
                        recommended_limit=round(float(top_cat.amount) * 0.8, -2), # -20% от текущей траты
                        severity="warning"
                    )
                )

            return AIAdvisorResponse(
                year=year,
                month=month,
                markdown_insights=fallback_markdown,
                widgets=fallback_widgets
            )

        # 3. Парсинг гибридного ответа от LLM
        if "===JSON_WIDGETS===" not in raw_text:
            return AIAdvisorResponse(year=year, month=month, markdown_insights=raw_text, widgets=[])

        parts = raw_text.split("===JSON_WIDGETS===")
        markdown_part = parts[0].strip()
        json_part = parts[1].strip()

        # Очищаем возможные теги ```json
        json_part_clean = re.sub(r"^```[a-zA-Z]*\n?|```$", "", json_part, flags=re.MULTILINE).strip()

        parsed_widgets = []
        try:
            parsed_json = json.loads(json_part_clean)
            widgets_raw = parsed_json.get("widgets", [])
            
            for w in widgets_raw:
                w_type = w.get("type")
                if w_type == "goal_progress":
                    parsed_widgets.append(GoalProgressBarWidget.model_validate(w))
                elif w_type == "category_limit":
                    parsed_widgets.append(CategoryLimitWidget.model_validate(w))
        except Exception as e:
            print(f"[AI Advisor Warning] Не удалось распарсить JSON виджетов: {e}")

        return AIAdvisorResponse(
            year=year,
            month=month,
            markdown_insights=markdown_part,
            widgets=parsed_widgets
        )