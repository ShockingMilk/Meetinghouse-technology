from apps.inventory.models import RoomAssessment, RoomAssessmentArea

AREA_FIELDS = {
    RoomAssessmentArea.AUDIO: ("audio_status", "Audio"),
    RoomAssessmentArea.VIDEO: ("video_status", "Video"),
    RoomAssessmentArea.NETWORK: ("network_status", "Network"),
    RoomAssessmentArea.PRINTING: ("printing_status", "Printing"),
    RoomAssessmentArea.ASSISTIVE_LISTENING: (
        "assistive_listening_status",
        "Assistive listening",
    ),
    RoomAssessmentArea.POWER: ("power_status", "Power"),
}


def attach_assessment_comparisons(assessments):
    """
    Attach comparison data to each assessment in newest-first order.

    Each assessment is compared with the nearest older assessment that
    shares at least one explicitly assessed area.
    """
    assessments = list(assessments)

    for index, current in enumerate(assessments):
        current_scope = set(current.assessed_areas or [])
        current.comparison_items = []
        current.comparison_assessment = None

        if not current_scope:
            continue

        for previous in assessments[index + 1 :]:
            previous_scope = set(previous.assessed_areas or [])
            shared_areas = current_scope & previous_scope

            if not shared_areas:
                continue

            current.comparison_assessment = previous

            for area, (status_field, label) in AREA_FIELDS.items():
                if area not in shared_areas:
                    continue

                current_status = getattr(current, status_field)
                previous_status = getattr(previous, status_field)

                current.comparison_items.append(
                    {
                        "area": area,
                        "label": label,
                        "current_status": getattr(
                            current, f"get_{status_field}_display"
                        )(),
                        "previous_status": getattr(
                            previous,
                            f"get_{status_field}_display",
                        )(),
                        "changed": current_status != previous_status,
                    }
                )

            # The first older assessment with overlapping scope is the
            # nearest comparable record. Do not skip it for a later match.
            break

    return assessments
