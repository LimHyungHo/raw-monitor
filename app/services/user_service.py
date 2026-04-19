from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self):
        self.user_repository = UserRepository()

    def get_user(self, *, user_id=None, email=None):
        if user_id is not None:
            return self.user_repository.get_user_by_id(user_id)
        if email:
            return self.user_repository.get_user_by_email(self.normalize_email(email))
        return None

    def list_users(self, *, email=None, name=None):
        if email:
            user = self.user_repository.get_user_by_email(self.normalize_email(email))
            return [user] if user else []
        if name:
            normalized_name = self.normalize_name(name)
            return self.user_repository.list_users_by_name(normalized_name)
        return []

    def register_user(self, *, email, name=None, is_active=1):
        normalized_email = self.normalize_email(email)
        user_id = self.user_repository.upsert_user(
            email=normalized_email,
            name=name,
            is_active=is_active,
        )
        return self.user_repository.get_user_by_id(user_id)

    def normalize_email(self, email):
        normalized_email = (email or "").strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("유효한 이메일 주소가 필요합니다.")
        return normalized_email

    def normalize_name(self, name):
        normalized_name = (name or "").strip()
        if not normalized_name:
            raise ValueError("이름이 필요합니다.")
        return normalized_name
