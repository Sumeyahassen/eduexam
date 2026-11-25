from rest_framework.permissions import BasePermission

from .models import User


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.SUPER_ADMIN
        )


class IsInstAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in (User.Role.INST_ADMIN, User.Role.SUPER_ADMIN)
        )


class IsExaminer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in (
                User.Role.EXAMINER,
                User.Role.INST_ADMIN,
                User.Role.SUPER_ADMIN,
            )
        )


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.STUDENT
        )
