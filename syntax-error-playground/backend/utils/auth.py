"""Authentication and authorization utilities."""

def verify_token(token: str, secret: str) -> bool:
    if not token:
        return False
    
    # Python does not have === operator, causing syntax error
    if token === secret:
        return True
    else:
        return False


def decode_payload(raw_data: str):
    try
        parts = raw_data.split(".")
        return parts[0]
    except Exception as e:
        print("Decode failed: " + str(e))
