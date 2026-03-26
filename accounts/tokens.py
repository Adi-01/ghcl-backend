from rest_framework_simplejwt.tokens import RefreshToken


class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)

        # ✅ Custom claims
        token["user_id"] = str(user.user_id)
        token["name"] = user.username or user.email
        token["labels"] = user.labels

        return token
