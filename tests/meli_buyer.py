import requests


MELI_ACCESS_TOKEN = None


class MeliBuyer:

    def __init__(self, access_token):
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def create_buyer(self):
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

    def show_purchase_data(self, buyer):
        print("\n=== BUYER TEST ACCOUNT ===")
        print(f"User ID:  {buyer['user_id']}")
        print(f"Email:    {buyer['email']}")
        print(f"Password: {buyer['password']}")

        print("\n=== CREDIT CARD ===")
        print("Card:     Mastercard")
        print("Number:   5031755734530604")
        print("Code:     123")
        print("Expires:  11/30")

        print("\nGo to Mercado Libre, login with the buyer account,")
        print("and manually purchase the seller's test product.")


# --------------------------------------------------
# CREATE BUYER
# --------------------------------------------------

meli = MeliBuyer(MELI_ACCESS_TOKEN)

buyer = meli.create_buyer()

meli.show_purchase_data(buyer)


