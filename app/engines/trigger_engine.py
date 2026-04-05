from app.models import Trigger


def classify_triggers(triggers: list[Trigger]) -> list[Trigger]:
    """
    MVP simplu: momentan doar returnează trigger-ele.
    Mai târziu aici putem adăuga clustering, deduping semantic,
    prioritizare și scoring pe trigger.
    """
    return triggers
