import hashlib
import hmac
import json
import urllib.parse
from fastapi import Header, HTTPException


def parse_init_data(init_data: str) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


def validate_init_data(init_data: str, bot_token: str) -> dict:
    data = parse_init_data(init_data)
    received_hash = data.pop("hash", None)

    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="No user in initData")

    try:
        user = json.loads(user_raw)
        return {
            "user_id": int(user["id"]),
            "username": user.get("username"),
            "first_name": user.get("first_name"),
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid user payload") from exc


def get_tg_initdata_header(x_tg_initdata: str | None = Header(default=None)) -> str:
    if not x_tg_initdata:
        raise HTTPException(status_code=401, detail="Missing X-TG-INITDATA header")
    return x_tg_initdata
