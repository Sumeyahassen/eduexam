from rest_framework.exceptions import ValidationError


class TenantScopeMixin:
    """
    Resolves request.institution at view time (after DRF authentication).

    Resolution order:
      1. Already set by TenantMiddleware (header / subdomain)
      2. The authenticated user's own institution
      3. ValidationError 400 — no institution context, cannot proceed
    """

    def get_institution(self):
        # Already resolved by middleware
        if getattr(self.request, "institution", None):
            return self.request.institution

        # Fall back to the user's institution (covers superusers using the API
        # directly without sending X-Institution-Slug)
        user = self.request.user
        if user.is_authenticated and getattr(user, "institution_id", None):
            self.request.institution = user.institution
            return self.request.institution

        raise ValidationError(
            {"institution": "No institution context. Send X-Institution-Slug header."}
        )

    def perform_create(self, serializer):
        serializer.save(institution=self.get_institution())

    def get_queryset(self):
        institution = self.get_institution()
        return super().get_queryset().filter(institution=institution)
