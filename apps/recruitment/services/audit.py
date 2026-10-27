from apps.recruitment.models import AuditEvent


def record(owner, action, obj, **details):
    # Callers pass identifiers/field names/stages only, never resume text or credentials.
    return AuditEvent.objects.create(
        owner=owner,
        action=action,
        target_type=obj._meta.model_name,
        target_id=str(obj.pk),
        details=details,
    )
