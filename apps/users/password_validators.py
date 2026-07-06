"""
Enhanced password validation for NexusIDE.
Enforces strong passwords with common pattern detection.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """
    Validates passwords against common patterns and weaknesses.
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Not a common password
    - Not similar to username
    """

    COMMON_PASSWORDS = {
        'password', 'password123', '12345678', 'qwerty123', 'abc123',
        'letmein', 'welcome', 'monkey', 'dragon', 'master', 'login',
        'princess', 'football', 'shadow', 'sunshine', 'trustno1',
        'iloveyou', 'batman', 'access', 'hello', 'charlie', 'passw0rd',
        'admin', 'admin123', 'root', 'toor', 'pass', 'test', 'guest',
        'master', 'changeme', 'default', '123456', '1234567', '123456789',
    }

    def validate(self, password, user=None):
        errors = []

        # Length check
        if len(password) < 8:
            errors.append(
                ValidationError(
                    _('Password must be at least 8 characters long.'),
                    code='password_too_short',
                )
            )

        # Uppercase check
        if not re.search(r'[A-Z]', password):
            errors.append(
                ValidationError(
                    _('Password must contain at least one uppercase letter.'),
                    code='password_no_uppercase',
                )
            )

        # Lowercase check
        if not re.search(r'[a-z]', password):
            errors.append(
                ValidationError(
                    _('Password must contain at least one lowercase letter.'),
                    code='password_no_lowercase',
                )
            )

        # Digit check
        if not re.search(r'\d', password):
            errors.append(
                ValidationError(
                    _('Password must contain at least one digit.'),
                    code='password_no_digit',
                )
            )

        # Common password check
        if password.lower() in self.COMMON_PASSWORDS:
            errors.append(
                ValidationError(
                    _('This password is too common. Please choose a stronger one.'),
                    code='password_too_common',
                )
            )

        # Similar to username check
        if user and user.username:
            if user.username.lower() in password.lower():
                errors.append(
                    ValidationError(
                        _('Password cannot be similar to your username.'),
                        code='password_similar_to_username',
                    )
                )

        # Sequential characters check
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            errors.append(
                ValidationError(
                    _('Password cannot contain sequential numbers.'),
                    code='password_sequential_numbers',
                )
            )

        # Repeated characters check
        if re.search(r'(.)\1{2,}', password):
            errors.append(
                ValidationError(
                    _('Password cannot contain repeated characters (e.g., "aaa").'),
                    code='password_repeated_chars',
                )
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            'Password must be at least 8 characters long, contain uppercase, '
            'lowercase, and digit characters, and cannot be a common password.'
        )


class NoSpecialCharValidator:
    """Optional: Require special characters for extra security."""

    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _('Password must contain at least one special character.'),
                code='password_no_special',
            )

    def get_help_text(self):
        return _('Password must contain at least one special character (!@#$%^&*() etc).')
