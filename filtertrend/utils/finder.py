from difflib import SequenceMatcher
from typing import List


class TrendFinder:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def _is_similar(self, a: str, b: str) -> bool:
        return SequenceMatcher(None, a, b).ratio() >= self.threshold

    def find_trends(self, filtered_items: List[dict]) -> List[dict]:
        """Group similar items and return unique representatives."""
        groups = []
        for item in filtered_items:
            text = (item.get("desc") or item.get("text") or "").lower()
            if not text:
                continue

            matched = False
            for group in groups:
                if any(self._is_similar(text, g["text"]) for g in group["items"]):
                    group["items"].append({"text": text, "item": item})
                    matched = True
                    break
            if not matched:
                groups.append({"items": [{"text": text, "item": item}]})

        representatives = []
        for group in groups:
            sorted_group = sorted(
                group["items"],
                key=lambda x: (x["item"].get("stats", {}).get("playCount", 0)),
                reverse=True,
            )
            rep = sorted_group[0]["item"]
            rep["_group_size"] = len(group["items"])
            representatives.append(rep)
        return representatives
