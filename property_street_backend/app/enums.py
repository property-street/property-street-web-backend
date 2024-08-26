import enum

class EmailManagementReasonChoice(enum.Enum):
    email_verification = 'email-verification'
    password_change = 'password-change'
    verified = 'verified'