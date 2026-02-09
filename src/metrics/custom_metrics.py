"""
Custom metrics for tracking junior-senior dynamics.
"""

from prometheus_client import Counter, Gauge, Histogram

# Junior question tracking
junior_questions_total = Counter(
    "junior_questions_total",
    "Questions asked by junior developers",
    ["junior_id", "resulted_in_change", "category"],
)

# Categories of junior questions
# - assumption_challenge: "Why do we do it this way?"
# - edge_case_discovery: "What if user does X?"
# - modern_alternative: "Could we use [new framework]?"
# - complexity_reduction: "Is this really necessary?"
# - documentation_gap: "How does this work?"
# - fresh_knowledge: "In bootcamp we learned X"

# Senior response patterns
senior_pause_before_answer = Histogram(
    "senior_response_pause_seconds",
    "Time senior pauses to think before answering junior",
    ["senior_id", "question_category"],
    buckets=[0, 2, 5, 10, 30, 60],  # Ideally 2-5 seconds
)

senior_learned_from_junior = Counter(
    "senior_learned_from_junior_total",
    "Times senior updated knowledge based on junior input",
    ["senior_id", "junior_id", "learning_type"],
)

# Learning types:
# - technology_update: New tool/framework
# - assumption_invalidated: Constraint no longer true
# - edge_case_found: Junior caught bug
# - complexity_reduced: Junior simplification worked

# Team health indicators
junior_question_rate = Gauge(
    "junior_question_rate_per_sprint",
    "Number of questions juniors ask per sprint",
    ["junior_id"],
)

question_dismissal_rate = Gauge(
    "question_dismissal_rate",
    "Percentage of junior questions dismissed without consideration",
    ["senior_id"],
)

# Healthy thresholds:
# - junior_question_rate: 15-20 per sprint (good)
# - question_dismissal_rate: < 20% (healthy culture)
# - senior_learned_from_junior: > 0.05 per sprint (learning happening)

# Reverse mentorship tracking
reverse_mentorship_events = Counter(
    "reverse_mentorship_total",
    "Junior teaching senior",
    ["junior_id", "senior_id", "topic"],
)

# Topics:
# - modern_framework: New tool/library
# - accessibility: A11y best practices
# - recent_idiom: Language features
# - user_perspective: UX insights
