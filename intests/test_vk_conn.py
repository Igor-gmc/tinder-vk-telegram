import requests
import os
from dotenv import load_dotenv

load_dotenv()

class VK:

   def __init__(self, access_token, user_id, version='5.199'):
       self.token = access_token
       self.id = user_id
       self.version = version
       self.params = {'access_token': self.token, 'v': self.version}


   def users_info(self):
       url = 'https://api.vk.com/method/users.get'
       params = {'user_ids': self.id}
       response = requests.get(url, params={**self.params, **params})
       return response.json()



access_token = os.getenv('VK_TOKEN')
user_id = os.getenv('VK_APP_ID')
vk = VK(access_token, user_id)

print(vk.users_info())