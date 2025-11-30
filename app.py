import streamlit as st
import datetime
import re # 正则清洁工，专门处理乱码
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef Fusion Pro",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. 深度 CSS 优化 (黑金风格) ---
st.markdown("""
<style>
    /* 全局字体 */
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    
    /* 调整底部留白 */
    .block-container {padding-bottom: 100px;}
    
    /* 报告卡片：黑金风格 */
    .report-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        border-left: 6px solid #C5A059; /* 香槟金 */
        margin-top: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    
    /* 菜名标题 */
    .dish-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        line-height: 1.4;
    }
    
    /* 强制链接样式 */
    .dish-link {
        color: #0056b3 !important;
        text-decoration: underline !important;
        cursor: pointer;
    }
    
    /* 核心章节标题 (H4) */
    h4 {
        color: #C5A059 !important;
        font-size: 1.05rem !important;
        font-weight: bold !important;
        margin-top: 20px !important;
        margin-bottom: 8px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* 正文文字 */
    p, li {
        font-size: 1rem;
        line-height: 1.6;
        color: #333;
        margin-bottom: 10px;
    }
    
    /* 摆盘美学高亮块 */
    .plating-box {
        background-color: #F8F8F8;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #333;
        margin-top: 10px;
        color: #555;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 密钥管理 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    with st.expander("🔑 API Key 配置"):
        if not deepseek_key:
            deepseek_key = st.text_input("DeepSeek Key", type="password")
        if not tavily_key:
            tavily_key = st.text_input("Tavily Key", type="password")
    
    if st.button("🗑️ 清空聊天记录", type="secondary"):
        st.session_state.messages = []
        st.rerun()

# --- 5. 标题 ---
st.title("👨‍🍳 行政总厨 (纯净版)")
st.caption("v16.0: 稳定快速 • 视觉美学 • 研发必备")

# --- 6. 核心 Prompt ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT = """
你是一名精通**【中西融合菜】**的行政总厨。
用户需求："{user_input}"
市场情报："{evidence}"

请提供 **3个** 高溢价的研发方案。

⚠️ **格式铁律（违反会导致乱码）：**
1.  **纯 HTML 输出：** 不要用 ```html 包裹。
2.  **不要缩进：** 所有 HTML 标签必须顶格写，行首不要有空格。
3.  **链接格式：** `<a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a>`

输出模板（直接输出 HTML）：
<div class="report-card">
<div class="dish-title">1. <a href="[https://www.google.com/search?q=菜名&tbm=isch](https://www.google.com/search?q=菜名&tbm=isch)" class="dish-link" target="_blank">菜名</a></div>
<h4>💡 中西融合灵感</h4>
<p>解释融合点...</p>
<h4>👨‍🍳 核心食材与技法</h4>
<p>列出关键材料...</p>
<h4>🎨 摆盘美学 (Plating)</h4>
<div class="plating-box">
<p><strong>器皿：</strong>...</p>
<p><strong>构图：</strong>...</p>
</div>
</div>
"""

# --- 7. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# --- 8. 交互区域 (纯净输入框) ---
user_input = st.chat_input("输入研发需求（例如：做一道适合秋季的创意鸭肉菜）...")

# --- 执行逻辑 ---
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key，请在侧边栏配置")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 总厨正在设计方案..."):
                search_query = f"{user_input} 高端摆盘 中西融合菜 做法 创意 plating"
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.7)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", FUSION_PROMPT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "user_input": user_input, 
                    "evidence": evidence
                })
                
                # --- 🔥 强力清洁工 (保留这个逻辑，防乱码) ---
                # 1. 去掉 ```html 和 ```
                response = re.sub(r"```[a-zA-Z]*", "", response)
                response = response.replace("```", "")
                
                # 2. 去掉每一行的缩进
                cleaned_lines = [line.strip() for line in response.split('\n')]
                response = "\n".join(cleaned_lines)

                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # 下载按钮
                now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
                st.download_button(
                    label="📥 下载这份研发报告",
                    data=response,
                    file_name=f"研发方案_{now_str}.html",
                    mime="text/html"
                )

        except Exception as e:
            st.error(f"运行出错: {e}")
