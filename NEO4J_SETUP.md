# Neo4j Setup Guide

## Установка Neo4j

### Вариант 1: Neo4j Aura (Cloud - Free Tier)

1. Зарегистрируйтесь на [Neo4j Aura](https://neo4j.com/cloud/aura/)
2. Создайте бесплатный инстанс (Free tier)
3. Скопируйте connection URI и password

### Вариант 2: Neo4j Desktop (Local)

1. Скачайте [Neo4j Desktop](https://neo4j.com/download/)
2. Установите и создайте новый проект
3. Создайте локальную базу данных
4. Запустите базу данных

## Конфигурация

Добавьте в `.env` файл:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Или для Neo4j Aura:
# NEO4J_URI=neo4j+s://xxx.neo4j.io
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your_aura_password
```

## Структура графа

### 6 Node Types:

1. **Profile** - Профили пользователей
   - Properties: `username`, `followers`, `following`, `videos`, `verified`, `name`, `bio`, `avatar`

2. **Video** - Видео
   - Properties: `url`, `views`, `likes`, `comments`, `shares`, `description`, `cover_url`, `uts_score`

3. **Hashtag** - Хэштеги
   - Properties: `name`, `usage_count`

4. **Song** - Музыка/звуки
   - Properties: `id`, `title`, `author`, `usage_count`

5. **Location** - Локации (опционально)
   - Properties: `name`, `usage_count`

6. **Trend** - Вертикали/категории
   - Properties: `vertical`, `video_count`

### 5 базовых Edge Types (из 27):

1. **CREATED_BY** - `(Video)-[:CREATED_BY]->(Profile)`
2. **TAGGED_WITH** - `(Video)-[:TAGGED_WITH]->(Hashtag)`
3. **USES_SOUND** - `(Video)-[:USES_SOUND]->(Song)`
4. **SIMILAR_VISUAL** - `(Video)-[:SIMILAR_VISUAL {similarity: 0.85}]->(Video)`
5. **BELONGS_TO** - `(Video)-[:BELONGS_TO]->(Trend)`

## Использование

### Программное использование:

```python
from filtertrend.core import get_graph, Neo4jGraph

# Получить singleton экземпляр
graph = get_graph()
if graph:
    # Работа с графом
    graph.create_profile_node("username", channel_data)
    graph.save_video_with_relationships(video_url, video_data, username, vertical)
```

### Миграция данных:

```python
from filtertrend.core import migrate_all_profiles_to_graph, migrate_all_trends_to_graph

# Мигрировать все профили
migrate_all_profiles_to_graph()

# Мигрировать все тренды
migrate_all_trends_to_graph(limit=100)
```

## Запросы Cypher

### Найти похожие видео:

```cypher
MATCH (v:Video {url: $video_url})-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(similar:Video)
WHERE v <> similar
RETURN similar.url, similar.views, COUNT(h) AS common_tags
ORDER BY common_tags DESC
LIMIT 10
```

### Получить видео профиля:

```cypher
MATCH (v:Video)-[:CREATED_BY]->(p:Profile {username: $username})
RETURN v.url, v.views, v.likes
ORDER BY v.views DESC
LIMIT 30
```

## Примечания

- Neo4j интеграция опциональна - если Neo4j недоступен, приложение продолжит работать
- Все операции с Neo4j не блокируют основной поток
- Для production рекомендуется использовать Neo4j Aura
