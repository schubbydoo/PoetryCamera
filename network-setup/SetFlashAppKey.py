import os
import base64

secret_key = os.urandom(24)
encoded_key = base64.b64encode(secret_key).decode('utf-8')
print(encoded_key)

