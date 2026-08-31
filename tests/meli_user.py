import requests


class MeliVenta:

    def __init__(self, access_token):
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def create_seller_user(self):
        url = f"{self.base_url}/users/test_user"

        response = requests.post(
            url,
            headers=self.headers,
            json={"site_id": "MLA"}
        )

        response.raise_for_status()

        data = response.json()

        return {
            "user_id": data["id"],
            "email": data["email"],
            "password": data["password"],
        }

    def get_seller_token(self, client_id, client_secret, code):
        url = f"{self.base_url}/oauth/token"

        response = requests.post(
            url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": "https://httpbin.org/get"
            }
        )

        response.raise_for_status()

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"]
        }


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MELI_ACCESS_TOKEN = None



# --------------------------------------------------
# SELLER
# --------------------------------------------------

meli = MeliVenta(MELI_ACCESS_TOKEN)

seller = meli.create_seller_user()


print("\n=== SELLER ===")
print(f"User ID:       {seller['user_id']}")
print(f"Email:         {seller['email']}")
print(f"Password:      {seller['password']}")


#enter in another browser with those creds.
#after the login, use the url with your main app user code and allow the app.
#https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id=CLIENT_ID&redirect_uri=https://httpbin.org/get

#CLIENT_ID is from your main app
#CLIENT_SECRET is from your main app
#SELLER_CODE is the code you just got from seller test.

#UNNCOMENT AND RUN:

CLIENT_ID = None
CLIENT_SECRET = None
SELLER_CODE = None

if CLIENT_ID:
    tokens = meli.get_seller_token(
        CLIENT_ID,
        CLIENT_SECRET,
        SELLER_CODE
    )
    print("\n=== SELLER TOKENS ===")
    print(f"Access Token:  {tokens['access_token']}")
    print(f"Refresh Token: {tokens['refresh_token']}")
