import requests

# Also authenticates the user
from api.gcp_services import get_local_firebase_setting, setup_firebase
from firebase_admin import auth

config = get_local_firebase_setting()
app = setup_firebase(config, use_emulator=True)


DEFAULT_EMAIL = "test@example.com"
DEFAULT_PASSWORD = "password123"

AUTH_URL = "http://{host}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"


def generate_token2(uid: str):
    """
    Generates a custom token for the user. Cannot be used with id_token.
    :param uid:
    :return:
    """
    return auth.create_custom_token(uid)


def generate_token(email: str | None = None, password: str | None = None) -> str:
    """
    Generates a custom token for the user.

    :param email: The email of the user
    :param password: The password of the user
    :return: The ID token used with `auth.verify_id_token`
    """
    emulator_auth_url = AUTH_URL.format(host=config.get("auth"))
    json_data = {
        "email": email or DEFAULT_EMAIL,
        "password": password or DEFAULT_PASSWORD,
        "returnSecureToken": True,
    }

    # The key is required for the emulator but can be anything
    params = {"key": "anykey"}
    response = requests.post(emulator_auth_url, json=json_data, params=params)
    if not response.status_code == 200:
        raise ValueError(f"Error signing in: {response.json()}")

    # The ID token is used for the Authorization header
    id_token = response.json().get("idToken") or ""
    print(f"ID Token: {id_token}")
    return id_token


def create_user(email: str | None = None, password: str | None = None):
    email = email or DEFAULT_EMAIL
    try:
        user = auth.get_user_by_email(email)
        if user:
            return user
    except auth.UserNotFoundError as e:
        print(f"User not found: {e}")
        return auth.create_user(
            email=email, password=password or DEFAULT_PASSWORD, display_name="Test User"
        )


def call_protected_endpoint(email: str | None = None):
    user = create_user(email)
    token = generate_token(user.email)

    headers = {"Authorization": f"Bearer {token}"}
    return requests.get("http://localhost:8000", headers=headers)


if __name__ == "__main__":
    resp = call_protected_endpoint()
    data = resp.json()
    print(data)
