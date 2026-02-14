"""Facebook Graph API 封裝 — 發布貼文"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

FB_API_VERSION = "v21.0"

FB_GRAPH_URL = f"https://graph.facebook.com/{FB_API_VERSION}"



def _get_config(brand: str = "default"):
    """取得 Facebook 設定 (根據品牌)"""
    if brand == "houjiazai":
        token = os.getenv("FB_PAGE_ACCESS_TOKEN_HOUJIAZAI")
        page_id = os.getenv("FB_PAGE_ID_HOUJIAZAI")
        brand_name = "厚家載藥師"
    else:
        token = os.getenv("FB_PAGE_ACCESS_TOKEN")
        page_id = os.getenv("FB_PAGE_ID")
        brand_name = "永芯長照"

    if not token or not page_id:
        raise ValueError(
            f"缺少 {brand_name} 的 Facebook 設定！請在 .env 檔設定對應的 Token 和 Page ID"
        )
    print(f"Debug: Loaded config for brand='{brand}'. Page ID: {page_id}")
    return token, page_id



def _raise_with_details(resp):
    """解析 FB API 錯誤並拋出有意義的訊息"""
    try:
        err = resp.json().get("error", {})
        msg = err.get("message", resp.text)
        code = err.get("code", resp.status_code)
        raise RuntimeError(f"Facebook API 錯誤 ({code}): {msg}")
    except (ValueError, KeyError):
        resp.raise_for_status()



# 設定 Retry 機制
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def post_text_only(message: str, brand: str = "default") -> dict:
    """發布純文字貼文。"""
    token, page_id = _get_config(brand)
    url = f"{FB_GRAPH_URL}/{page_id}/feed"
    payload = {
        "message": message,
        "access_token": token,
    }
    
    session = _get_session()
    try:
        resp = session.post(url, data=payload, timeout=60)
        if not resp.ok:
            _raise_with_details(resp)
        return resp.json()
    except requests.exceptions.RequestException as e:
         raise RuntimeError(f"網路連線失敗，請檢查您的網路狀態。\n錯誤詳情: {e}")


def post_with_image(message: str, image_path: str, brand: str = "default") -> dict:
    """發布含圖片的貼文。"""
    token, page_id = _get_config(brand)
    image_file = Path(image_path)

    if not image_file.exists():
        raise FileNotFoundError(f"圖片檔案不存在：{image_path}")

    upload_url = f"{FB_GRAPH_URL}/{page_id}/photos"
    
    session = _get_session()
    # 圖片上傳通常需要較長時間，設定 120 秒 timeout
    try:
        with open(image_file, "rb") as f:
            files = {"source": (image_file.name, f, "image/png")}
            data = {
                "message": message,
                "access_token": token,
            }
            resp = session.post(upload_url, data=data, files=files, timeout=120)

        if not resp.ok:
            _raise_with_details(resp)
        return resp.json()
    except requests.exceptions.RequestException as e:
         raise RuntimeError(f"網路連線失敗 (Timeline Timeout)，請檢查您的網路狀態或 VPN。\n錯誤詳情: {e}")


def verify_token(brand: str = "default") -> dict:
    """
    驗證 Page Access Token 是否有效。
    Returns: token debug info
    """
    token, page_id = _get_config(brand)
    url = f"{FB_GRAPH_URL}/{page_id}"
    params = {
        "fields": "name,id",
        "access_token": token,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

