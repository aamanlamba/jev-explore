"""Evaluate news headlines across multiple TypeSafe dimensions."""
from __future__ import annotations

from dataclasses import dataclass, field

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeError

CATEGORIES = [
    "Politics",
    "Business",
    "Technology",
    "Sports",
    "Entertainment",
    "Health",
    "Science",
    "World",
]

MATCH_THRESHOLD = 0.5


@dataclass
class HeadlineResult:
    headline: str
    categories: dict[str, float] = field(default_factory=dict)
    sentiment: str = ""
    sentiment_probabilities: dict[str, float] = field(default_factory=dict)
    sentiment_confidence: float = 0.0
    sensationalism_score: float = 0.0
    breaking_probability: float = 0.0
    error: str | None = None
    error_type: str | None = None

    def matched_categories(self, threshold: float = MATCH_THRESHOLD) -> list[str]:
        return [name for name, prob in self.categories.items() if prob > threshold]

    def is_breaking(self, threshold: float = MATCH_THRESHOLD) -> bool:
        return self.breaking_probability > threshold


def build_questions() -> dict[str, Choice | Noul | Score]:
    questions: dict[str, Choice | Noul | Score] = {
        f"category_{name.lower()}": Noul(
            instructions=f"The headline is about {name}.",
        )
        for name in CATEGORIES
    }
    questions["sentiment"] = Choice(
        instructions="What is the overall sentiment or tone of this headline?",
        criteria={
            "positive": "Upbeat, favorable, or celebratory framing",
            "neutral": "Matter-of-fact, no clear positive or negative framing",
            "negative": "Unfavorable, alarming, or critical framing",
        },
    )
    questions["sensationalism"] = Score(
        instructions="How sensational or clickbait-y is this headline's framing?",
        criteria=[
            "Straightforward and factual, no exaggeration",
            "Somewhat attention-grabbing, mild exaggeration",
            "Highly sensational, clickbait framing",
        ],
    )
    questions["breaking"] = Noul(
        instructions="This headline describes breaking or time-sensitive news.",
    )
    return questions


def evaluate_headline(client: TypeSafeClient, headline: str) -> HeadlineResult:
    result = HeadlineResult(headline=headline)
    try:
        response = client.system_one(state=headline, questions=build_questions())
    except TypeSafeError as exc:
        result.error = str(exc)
        result.error_type = type(exc).__name__
        return result

    for name in CATEGORIES:
        answer = response.answers[f"category_{name.lower()}"]
        result.categories[name] = answer.noul

    sentiment_answer = response.answers["sentiment"]
    result.sentiment = sentiment_answer.choice
    result.sentiment_probabilities = dict(sentiment_answer.probabilities)
    result.sentiment_confidence = sentiment_answer.confidence

    result.sensationalism_score = response.answers["sensationalism"].score
    result.breaking_probability = response.answers["breaking"].noul

    return result


def evaluate_headlines(client: TypeSafeClient, headlines: list[str]) -> list[HeadlineResult]:
    return [evaluate_headline(client, headline) for headline in headlines]
