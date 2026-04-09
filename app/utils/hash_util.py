import hashlib

def generate_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()