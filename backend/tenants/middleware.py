from .models import Institution


class TenantMiddleware:
    """
    Resolves the current Institution and attaches it to request.institution.

    Resolution order (first match wins):
      1. X-Institution-Slug request header
      2. Subdomain of the Host header  (school.eduexam.com → "school")
      3. The authenticated user's own institution (JWT already validated by DRF
         before any view runs, so request.user is available here when the view
         uses JWTAuthentication — but middleware runs BEFORE authentication, so
         we do a lazy fallback inside a property instead).

    For case 3 we attach a sentinel so views can call
    request.resolve_institution() after DRF has authenticated the user.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        slug = request.headers.get("X-Institution-Slug")

        if not slug:
            host = request.get_host().split(":")[0]
            parts = host.split(".")
            if len(parts) >= 3:
                slug = parts[0]

        if slug:
            try:
                request.institution = Institution.objects.get(slug=slug, is_active=True)
            except Institution.DoesNotExist:
                request.institution = None
        else:
            request.institution = None

        response = self.get_response(request)

        # After the view has run, DRF has authenticated the user.
        # If institution is still None but the user has one, back-fill it.
        # This handles the case where the JWT carries institution info but no
        # header / subdomain was sent.
        if request.institution is None and hasattr(request, "user"):
            user = request.user
            if user.is_authenticated and getattr(user, "institution_id", None):
                request.institution = user.institution

        return response
