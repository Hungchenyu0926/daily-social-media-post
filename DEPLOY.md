# 部署指南 (Deployment Guide)

本專案已準備好部署至 GitHub 與 Streamlit Cloud。請按照以下步驟操作。

## 1. 推送至 GitHub (Push to GitHub)

請在終端機 (Terminal) 中執行以下指令：

### 初始化 Git Repository (如果尚未執行)

```bash
git init
git add .
git commit -m "Initial commit"
```

### 建立 GitHub Repository 並推送

1. 前往 [GitHub New Repository](https://github.com/new) 建立一個新的 Repository (例如命名為 `daily-social-media-post`).
2. 複製 GitHub 提供的 HTTPS 或 SSH 網址 (例如 `https://github.com/username/daily-social-media-post.git`).
3. 回到終端機執行：

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/daily-social-media-post.git
git push -u origin main
```

*(請將上面的網址替換為您實際的 GitHub Repository 網址)*

---

## 2. 部署至 Streamlit Cloud

1. 前往 [Streamlit Cloud](https://share.streamlit.io/).
2. 點擊 **"New app"**.
3. 選擇 **"Use existing repo"**.
4. 選擇您剛剛建立的 GitHub Repository (`daily-social-media-post`).
5. **Main file path** 輸入 `app.py`.
6. 點擊 **"Advanced settings"** (或 **Manage app** > **Settings** > **Secrets**).

### 設定 Secrets (環境變數)

這是最重要的一步！Streamlit Cloud 不會讀取 `.env` 檔案，您必須手動設定 Secrets。
將您的 `.env` 文件內容複製並貼上到 Secrets 欄位中，格式如下：

```toml
GEMINI_API_KEY = "AIzaSy..."
FB_PAGE_ACCESS_TOKEN = "EAAKQ..."
FB_PAGE_ID = "9292..."
FB_PAGE_ACCESS_TOKEN_HOUJIAZAI = "EAAMt..."
FB_PAGE_ID_HOUJIAZAI = "1948..."
```

*(請直接複製您的 `.env` 內容，Streamlit 會自動解析)*

1. 點擊 **"Save"**.
2. 點擊 **"Deploy!"**.

---

## 疑難排解 (Troubleshooting)

- **ModuleNotFoundError**: 確認 `requirements.txt` 是否包含所有套件 (已自動為您建立).
- **Facebook API Error**: 確保 Secrets 中的 Token 與 `.env` 中的一致.
