"""Gemini API 封裝 — 純 REST API，不依賴任何 Google SDK"""

import json
import os
import io
import re
import base64
import requests as req
from pathlib import Path

from PIL import Image
from dotenv import load_dotenv


import streamlit as st
from prompts.article_prompt import get_system_prompt, get_article_prompt
from prompts.image_prompt import IMAGE_PROMPT_SYSTEM_PROMPT, get_image_prompt_request

load_dotenv()

# 改用 st.secrets，若沒有則 fallback 到 os.getenv (相容性)
try:
    API_KEY = st.secrets.get("GEMINI_API_KEY")
except FileNotFoundError:
    API_KEY = os.getenv("GEMINI_API_KEY")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _call_gemini(model: str, system_instruction: str, user_prompt: str, response_mime_type: str = None) -> str:
    """呼叫 Gemini REST API 生成文字"""
    if not API_KEY:
        raise ValueError("缺少 GEMINI_API_KEY！請檢查 secrets.toml 或 .env")

    url = f"{BASE_URL}/models/{model}:generateContent?key={API_KEY}"

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
    }

    if response_mime_type:
        payload["generationConfig"] = {
            "responseMimeType": response_mime_type,
        }

    resp = req.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()


    # 提取文字
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini 沒有回傳候選結果 (Candidates Empty)。Raw Data: {json.dumps(data)}")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    
    # 檢查是否因安全理由被擋
    if finish_reason and finish_reason != "STOP":
        safety_ratings = candidate.get("safetyRatings", [])
        raise RuntimeError(f"Gemini 生成中斷，原因: {finish_reason}。安全性評級: {json.dumps(safety_ratings)}")

    parts = candidate.get("content", {}).get("parts", [])
    if not parts:
         # 有時候雖然是 STOP，但沒有 content parts (極少見，但可能)
         raise RuntimeError(f"Gemini 回傳了 STOP 但沒有文字內容 (No Content Parts)。Raw Data: {json.dumps(data)}")

    return "".join(p.get("text", "") for p in parts)



def generate_article(raw_material: str, brand: str = "default") -> str:
    """根據原始素材生成衛教貼文。"""
    system_prompt = get_system_prompt(brand)
    return _call_gemini(
        model="gemini-2.5-flash",
        system_instruction=system_prompt,
        user_prompt=get_article_prompt(raw_material),
    )



def generate_image_prompts(article: str) -> list[dict]:
    """根據文章生成 3 組圖片 Prompt（JSON 格式）。"""
    text = _call_gemini(
        model="gemini-2.5-flash",
        system_instruction=IMAGE_PROMPT_SYSTEM_PROMPT,
        user_prompt=get_image_prompt_request(article),
        response_mime_type="application/json",
    )

    try:
        prompts = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            prompts = json.loads(match.group(1))
        else:
            raise ValueError(f"無法解析 Gemini 回傳的 JSON:\n{text}")

    return prompts


def generate_image(prompt: str, filename: str = "generated_image.png") -> Path:
    """使用 Gemini 3 Pro Image (Nano Banana Pro) 的原生圖片生成功能。"""
    # Nano Banana Pro ID: gemini-3-pro-image-preview
    url = f"{BASE_URL}/models/gemini-3-pro-image-preview:generateContent?key={API_KEY}"

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"Generate an image: {prompt}"}]}
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }

    resp = req.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini 未回傳結果：{data}")

    parts = candidates[0].get("content", {}).get("parts", [])

    # 從 parts 中找到圖片（inlineData）
    for part in parts:
        inline = part.get("inlineData")
        if inline and inline.get("mimeType", "").startswith("image/"):
            image_bytes = base64.b64decode(inline["data"])
            image_path = OUTPUT_DIR / filename
            img = Image.open(io.BytesIO(image_bytes))
            img.save(str(image_path))
            return image_path

    raise RuntimeError("Gemini 回傳中沒有圖片資料")
