#this SDK works to help meeeee mostly and maybe you in the implement of testing selling events.
#leaving you/me only with the task of going to meli with the buyer account and test the sell event.

import requests

class MeliVenta():
    
    def __init__(self, access_token):

        self.base_url = "https://api.mercadolibre.com"
        self.token =  "your token"
        self.header = {'Authorization': f'Bearer {access_token}', 'Content-type': 'application/json'}

    def create_users(self):
        vendedor = self._create_test_user()
        self.comprador =  self._create_test_user()
        print(f'data vendedor: {vendedor}')
        
    def _create_test_user(self):
        url = f'{self.base_url}/users/test_user'
        json = {"site_id":"MLA"}
        response = requests.post(url=url,headers=self.header,json=json).json()
        email_test = response.get('email')
        password = response.get('password')
        return email_test, password

    def _crate_test_user_token(self):
        print("Hello, Mercadolibre needs the following info in order to publicate the item in your user seller test account:\n")
        client_id = input("your client/app id (from dev app):\n")
        client_secret = input("your client secret (from dev app):\n")
        print(
            f"Copy and Paste this URL in your open user test account in Mercadolibre,\n"
            f"this would return the refresh token that you need in the following step.\n"
            f"https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id={client_id}&redirect_uri=https://httpbin.org/get\n"
        )
        refresh = input("\nyour refresh token (from vinculation of your test app):").replace('"','')

        payload = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': refresh,
            'redirect_uri': 'https://httpbin.org/get'
        }
        url = f'{self.base_url}/oauth/token'
        response = requests.post(url, data=payload)
        token_user_test = response.json().get('access_token')
        print(f"\nThis is your test user token: {token_user_test}")
        return token_user_test

    def publicate_item_test(self):

        user_test_token = self._crate_test_user_token()

        item_data = {
            "title": "Item de Prueba - Por favor, NO OFERTAR",
            "category_id": "MLA1104",
            "price": 1000,
            "currency_id": "ARS",
            "available_quantity": 100,
            "buying_mode": "buy_it_now",
            "listing_type_id": "bronze",
            "condition": "new",
            "attributes": [
                {
                    "id": "BRAND",
                    "value_name": "Marca Genérica"
                },
                {
                    "id": "MODEL",
                    "value_name": "Modelo de Prueba"
                }
            ],
            "description": {"plain_text": "Publicación de prueba técnica desde API."},
            "pictures": [
                {"source": "https://storage.googleapis.com/bucket_import_fotos/205310/foto_1.png"}
            ]
        }
        url = f'{self.base_url}/items'
        header = {'Authorization': f'Bearer {user_test_token}', 'Content-type': 'application/json'}
        response = requests.post(url, json=item_data, headers=header)
        if response.status_code == 201:
            print("\nProduct Publicated! (pictures may be need to be adjusted by hand in the website)\n\n")

            print(
                f"To test a purcharse, First enter your buyer test account (incognito mode).\n"
                f"{self.comprador}.\n"
                f"Use the following info to buy from the User Test\n"
                f"  CreditCard: Mastercard\n"
                f"  Number: 5031755734530604\n"
                f"  Code: 123\n"
                f"  ExpiresAt: 11/30")

        else:
            print(f"Error: {response.status_code}")
            print(response.json())
    

        
token = 'your dev seller token'
Meli =  MeliVenta(token)
#Meli.create_users()
Meli.publicate_item_test()

