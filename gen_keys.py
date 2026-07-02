from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

key = ec.generate_private_key(ec.SECP256R1())
pub = key.public_key()

priv_raw = key.private_numbers().private_value.to_bytes(32, 'big')
pub_raw = pub.public_numbers().encode_point()

print("PRIVATE:", base64.urlsafe_b64encode(priv_raw).rstrip(b'=').decode())
print("PUBLIC:", base64.urlsafe_b64encode(pub_raw).rstrip(b'=').decode())