"""
永芯居家長照機構 — 每日社群貼文自動化工作流程
Streamlit 主應用
"""

import streamlit as st
from pathlib import Path
import json
import sys

# 確保 project root 在 sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ─── Page Config ─── #
st.set_page_config(
    page_title="社群貼文寫手",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Debug: Print Session State
# st.write("Current Session State:", st.session_state)


# ─── Custom CSS ─── #
st.markdown("""
<style>
    /* 主容器 */
    .main .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }

    /* 步驟指示器 */
    .step-indicator {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 2rem;
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        font-weight: bold;
        font-size: 1rem;
    }
    .step-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .step-done {
        background: #4CAF50;
        color: white;
    }
    .step-pending {
        background: #e0e0e0;
        color: #999;
    }

    /* 文章預覽卡片 */
    .article-preview {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #333;
        line-height: 1.8;
        white-space: pre-wrap;
    }

    /* 圖片風格卡片 */
    .style-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    .style-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* 成功動畫 */
    .success-box {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }

    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Session State 初始化 ─── #
DEFAULTS = {
    "current_step": 1,
    "raw_material": "",
    "generated_article": "",
    "edited_article": "",
    "article_confirmed": False,
    "image_prompts": [],


    "selected_prompt_idx": None,
    "generated_image_path": None,
    "post_result": None,
}



for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─── Sidebar: 設定 & 工具 ─── #
with st.sidebar:
    st.markdown("### ⚙️ 設定")

    # 品牌選擇
    st.markdown("#### 🏥 選擇品牌/粉專")
    brand_map = {
        "default": "永芯居家長照",
        "houjiazai": "厚家載藥師",
    }
    
    # 確保 session_state 有 brand
    if "brand" not in st.session_state:
        st.session_state.brand = "default"

    def on_brand_change():
        """當品牌改變時，重置流程狀態"""
        for key, val in DEFAULTS.items():
            st.session_state[key] = val

    st.radio(
        "目前身分：",
        options=list(brand_map.keys()),
        format_func=lambda x: brand_map[x],
        key="brand", # 直接綁定到 session_state.brand
        on_change=on_brand_change
    )

    st.divider()

    # 檢查 API 設定狀態
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)

    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))

    
    # 檢查當前選擇品牌的 FB 設定
    if st.session_state.brand == "houjiazai":
        fb_token = os.getenv("FB_PAGE_ACCESS_TOKEN_HOUJIAZAI")
        fb_page = os.getenv("FB_PAGE_ID_HOUJIAZAI")
    else:
        fb_token = os.getenv("FB_PAGE_ACCESS_TOKEN")
        fb_page = os.getenv("FB_PAGE_ID")

    fb_ok = bool(fb_token) and bool(fb_page)

    st.markdown(f"- Gemini API: {'✅ 已設定' if gemini_ok else '❌ 未設定'}")
    st.markdown(f"- Facebook API ({brand_map[st.session_state.brand]}): {'✅ 已設定' if fb_ok else '❌ 未設定'}")

    if not gemini_ok or not fb_ok:
        st.warning(f"請在 `.env` 檔案中設定 {brand_map[st.session_state.brand]} 的 API 金鑰")

    st.divider()

    # FB Token 驗證
    if fb_ok:
        if st.button("🔍 驗證 Facebook Token"):
            try:
                from services.facebook_service import verify_token
                info = verify_token(st.session_state.brand) # Use .brand directly
                st.success(f"✅ Token 有效！粉專：{info.get('name', 'N/A')}")
            except Exception as e:
                st.error(f"Token 無效：{e}")

    st.divider()

    # 重置流程
    if st.button("🗑️ 重置整個流程", use_container_width=True):
        # 僅重置流程狀態，不重置品牌
        for key, val in DEFAULTS.items():
            st.session_state[key] = val
        st.rerun()

    st.divider()
    st.caption("社群貼文寫手 © 2026")



# ─── 步驟指示器 ─── #
def render_step_indicator():
    steps = ["素材輸入", "文章生成", "圖片Prompt", "圖片生成", "發布FB"]
    cols = st.columns(len(steps))
    for i, (col, label) in enumerate(zip(cols, steps), 1):
        with col:
            if i < st.session_state.current_step:
                st.markdown(f"<div style='text-align:center'><span class='step-badge step-done'>✓</span><br><small>{label}</small></div>", unsafe_allow_html=True)
            elif i == st.session_state.current_step:
                st.markdown(f"<div style='text-align:center'><span class='step-badge step-active'>{i}</span><br><small><b>{label}</b></small></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center'><span class='step-badge step-pending'>{i}</span><br><small>{label}</small></div>", unsafe_allow_html=True)
    st.divider()


# ─── Header ─── #
st.markdown("## 📝 社群貼文寫手")
st.caption("從素材到 Facebook 發布，一氣呵成")
render_step_indicator()


# ═══════════════════════════════════════════ #
#  STEP 1: 輸入素材 → 生成文章
# ═══════════════════════════════════════════ #
if st.session_state.current_step == 1:
    st.markdown("### 1️⃣ 輸入原始素材 / 知識點")
    st.info("💡 貼上你想轉化為衛教貼文的素材、新聞、知識點或重點整理。")

    raw = st.text_area(
        "原始素材",
        value=st.session_state.raw_material,
        height=250,
        placeholder="例：冬天長輩容易跌倒，居家環境可以怎麼預防？浴室加裝扶手、走道保持明亮...",
    )
    st.session_state.raw_material = raw

    col1, col2 = st.columns([1, 5])
    with col1:
        generate_btn = st.button("🚀 生成文章", type="primary", use_container_width=True)


    if generate_btn:
        if not raw.strip():
            st.warning("請先輸入素材！")
        else:

            with st.spinner("✨ AI 正在撰寫衛教貼文..."):
                try:
                    # Debug Info
                    st.write(f"Debug: 正在為品牌 '{st.session_state.brand}' 生成文章...")
                    
                    from services.gemini_service import generate_article
                    # Pass the selected brand to generate_article
                    article = generate_article(raw.strip(), brand=st.session_state.brand)
                    


                    st.write("Debug: 文章生成成功！長度:", len(article))
                    # st.write("Debug Preview:", article[:100] + "...")
                    
                    st.session_state.generated_article = article
                    st.session_state.edited_article = article
                    st.session_state.current_step = 2
                    st.rerun()


                except Exception as e:
                    st.error(f"生成失敗詳情：{str(e)}")
                    st.exception(e) # This prints the stack trace





# ═══════════════════════════════════════════ #
#  STEP 2: 編輯 & 確認文章
# ═══════════════════════════════════════════ #
elif st.session_state.current_step == 2:
    st.markdown("### 2️⃣ 編輯 & 確認文章")
    st.info("📝 可以直接在下方編輯文章，滿意後按「確認文章」。")

    edited = st.text_area(
        "文章內容（可編輯）",
        value=st.session_state.edited_article,
        height=400,
    )
    st.session_state.edited_article = edited


    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("⬅️ 返回修改素材", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.button("🔄 重新生成", use_container_width=True):
            with st.spinner("✨ 重新生成中..."):
                try:
                    from services.gemini_service import generate_article
                    article = generate_article(st.session_state.raw_material.strip(), brand=st.session_state.brand)
                    st.session_state.generated_article = article
                    st.session_state.edited_article = article
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失敗：{e}")
    with col3:
        if st.button("✅ 確認文章", type="primary", use_container_width=True):
            st.session_state.article_confirmed = True
            st.session_state.current_step = 3
            st.rerun()

    st.divider()

    # 預覽
    with st.expander("📱 手機預覽效果", expanded=True):
        st.markdown(f"<div class='article-preview'>{edited}</div>", unsafe_allow_html=True)



# ═══════════════════════════════════════════ #
#  STEP 3: 生成圖片 Prompt & 選擇
# ═══════════════════════════════════════════ #
elif st.session_state.current_step == 3:
    st.markdown("### 3️⃣ 選擇圖片風格")

    # 如果還沒生成圖片 prompts，先生成
    if not st.session_state.image_prompts:
        with st.spinner("🎨 AI 正在創作 3 種風格的影像描述..."):
            try:
                from services.gemini_service import generate_image_prompts
                prompts = generate_image_prompts(st.session_state.edited_article)
                st.session_state.image_prompts = prompts
                st.rerun()
            except Exception as e:
                st.error(f"生成圖片 Prompt 失敗：{e}")
                if st.button("🔄 重試"):
                    st.rerun()
                st.stop()

    # 顯示 3 種風格供選擇
    prompts = st.session_state.image_prompts

    for i, p in enumerate(prompts):
        with st.container():
            st.markdown(f"""
<div class='style-card'>
<h4>🎨 風格 {i+1}：{p.get('style_name_zh', '')} / {p.get('style_name_en', '')}</h4>
</div>
""", unsafe_allow_html=True)

            with st.expander(f"查看完整描述 - 風格 {i+1}"):
                st.markdown(f"**中文長描述：**\n{p.get('long_desc_zh', '')}")
                st.markdown(f"**English Long Description：**\n{p.get('long_desc_en', '')}")
                st.divider()
                st.markdown(f"**簡短提示語（中）：** {p.get('short_prompt_zh', '')}")
                st.markdown(f"**Short Prompt (EN)：** {p.get('short_prompt_en', '')}")

    # 選擇風格
    selected = st.radio(
        "選擇一個風格來生成圖片：",
        options=list(range(len(prompts))),
        format_func=lambda x: f"風格 {x+1}：{prompts[x].get('style_name_zh', '')}",
        horizontal=True,
    )
    st.session_state.selected_prompt_idx = selected

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("⬅️ 返回編輯文章", use_container_width=True):
            st.session_state.current_step = 2
            st.session_state.image_prompts = []
            st.rerun()
    with col2:
        if st.button("🔄 重新生成 Prompt", use_container_width=True):
            st.session_state.image_prompts = []
            st.rerun()

    if st.button("🖼️ 使用這個風格生成圖片", type="primary", use_container_width=True):
        st.session_state.current_step = 4
        st.rerun()


# ═══════════════════════════════════════════ #
#  STEP 4: 生成圖片
# ═══════════════════════════════════════════ #
elif st.session_state.current_step == 4:
    st.markdown("### 4️⃣ AI 圖片生成")

    idx = st.session_state.selected_prompt_idx
    selected_prompt = st.session_state.image_prompts[idx]

    st.info(f"🎨 正在使用風格：**{selected_prompt.get('style_name_zh', '')}**")

    if st.session_state.generated_image_path is None:
        with st.spinner("🖼️ Gemini Imagen 正在生成圖片...（約需 10-30 秒）"):
            try:
                from services.gemini_service import generate_image
                # 使用英文 short prompt 作為生成的 prompt（效果最好）
                prompt_text = selected_prompt.get("short_prompt_en", selected_prompt.get("long_desc_en", ""))
                image_path = generate_image(prompt_text, filename=f"post_image_{idx}.png")
                st.session_state.generated_image_path = str(image_path)
                st.rerun()
            except Exception as e:
                st.error(f"圖片生成失敗：{e}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 重試"):
                        st.rerun()
                with col2:
                    if st.button("⬅️ 換一個風格"):
                        st.session_state.current_step = 3
                        st.rerun()
                st.stop()

    # 顯示生成的圖片
    st.image(st.session_state.generated_image_path, caption="生成的圖片", use_container_width=True)

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("⬅️ 換風格", use_container_width=True):
            st.session_state.current_step = 3
            st.session_state.generated_image_path = None
            st.rerun()
    with col2:
        if st.button("🔄 重新生成圖", use_container_width=True):
            st.session_state.generated_image_path = None
            st.rerun()

    if st.button("📤 前往發布至 Facebook", type="primary", use_container_width=True):
        st.session_state.current_step = 5
        st.rerun()


# ═══════════════════════════════════════════ #
#  STEP 5: 預覽 & 發布至 Facebook
# ═══════════════════════════════════════════ #
elif st.session_state.current_step == 5:
    st.markdown("### 5️⃣ 預覽 & 發布至 Facebook")

    # 最終預覽
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown("**📄 文章內容：**")
        st.markdown(f"<div class='article-preview'>{st.session_state.edited_article}</div>", unsafe_allow_html=True)
    with col_img:
        st.markdown("**🖼️ 配圖：**")
        use_image = False
        if st.session_state.generated_image_path:
            st.image(st.session_state.generated_image_path, use_container_width=True)
            use_image = st.checkbox("✅ 一併上傳圖片", value=True)
        else:
            st.warning("沒有圖片（將發布純文字貼文）")

    st.divider()

    # 發布按鈕
    if st.session_state.post_result is None:
        
        # Debug: Check Credentials before posting
        current_brand = st.session_state.brand
        import os
        from services.facebook_service import _get_config
        try:
            d_token, d_page_id = _get_config(current_brand)
            st.info(f"🔍 準備發布身分：**{current_brand}**")
            st.caption(f"Debug Info: Page ID={d_page_id}, Token={d_token[:5]}...{d_token[-5:] if d_token else ''}")
        except Exception as e:
            st.error(f"無法讀取設定：{e}")

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            if st.button("⬅️ 返回", use_container_width=True):
                st.session_state.current_step = 4
                st.rerun()


        if st.button("🚀 確認發布至 Facebook", type="primary", use_container_width=True):
            with st.spinner("📤 正在發布至 Facebook..."):
                try:
                    from services.facebook_service import post_with_image, post_text_only

                    if st.session_state.generated_image_path and use_image:
                        result = post_with_image(
                            st.session_state.edited_article,
                            st.session_state.generated_image_path,
                            brand=st.session_state.brand
                        )
                    else:
                        result = post_text_only(st.session_state.edited_article, brand=st.session_state.brand)

                    st.session_state.post_result = result
                    st.rerun()
                except Exception as e:
                    st.error(f"發布失敗：{e}")
                    st.info("💡 請確認 .env 中的 FB_PAGE_ACCESS_TOKEN 和 FB_PAGE_ID 是否正確。")

    else:
        # 發布成功
        result = st.session_state.post_result
        st.markdown(f"""
<div class='success-box'>
    <h2>🎉 發布成功！</h2>
    <p>貼文已成功發布至 Facebook 粉絲專頁。</p>
    <p><small>Post ID: {result.get('id', result.get('post_id', 'N/A'))}</small></p>
</div>
""", unsafe_allow_html=True)

        st.balloons()

        if st.button("📝 建立新貼文", type="primary", use_container_width=True):
            # Reset all state
            for key, val in DEFAULTS.items():
                st.session_state[key] = val
            st.rerun()



# ─── Sidebar: 設定 & 工具 ─── #



