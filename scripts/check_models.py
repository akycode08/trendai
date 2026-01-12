import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("⚠️ ANTHROPIC_API_KEY не найден в .env")
    exit(1)

client = Anthropic(api_key=api_key)

print("🔍 Доступные модели Claude:")
print(" - claude-3-5-sonnet-20241022 (рекомендуется)")
print(" - claude-3-5-haiku-20241022 (быстрая)")
print(" - claude-3-opus-20240229 (мощная)")

print("\n🧪 Тест подключения...")
try:
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": "Hi"}]
    )
    print(f"✅ Подключение успешно! Ответ: {response.content[0].text[:50]}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
