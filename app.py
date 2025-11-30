import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
# --- 修复点：引入新的语音库 ---
from streamlit_mic_recorder import speech_to_text

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Voice",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入 CSS
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 15px; background: white; z-index: 999;}
    .block-container {padding-top: 2rem; padding-bottom: 12rem;}
    h1 {color: #1A1A1A;}
    .report-card {
        background-color: #fff;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        border-left: 6px solid #CCA352;
        margin-top: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }
    .dish-title {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .dish-title a {
        color: #0066cc !important;
        text-decoration: underline !important;
        cursor: pointer;
    }
    .fusion-badge {
        background-color: #1A1A1A;
        color: #CCA352;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        margin-left: 8px;
        vertical-align: middle;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 密钥管理 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    with st.expander("🔑 API Key 配置"):
        if not deepseek_key:
            deepseek_key = st.text_input("DeepSeek Key", type="password")
        if not tavily_key:
            tavily_key = st.text_input("Tavily Key", type="password")
    
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# --- 4. 标题 ---
st.title("👨‍🍳 行政总厨 (语音修复版)")
st.caption("v11.1: 点击下方麦克风即可说话 • 蓝色链接点击直达图片")

# --- 5. 核心 Prompt ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT = """
你是一名精通**【中西融合菜 (Fusion Cuisine)】**的行政总厨。
用户需求："{user_input}"
情报："{evidence}"

请提供 **3个** 中西结合的研发方案。

⚠️ **必须严格遵守的链接格式：**
提到具体的【菜名】时，必须使用 Markdown 链接格式，且链接地址必须是 Google 图片搜索。
格式：`[菜名](https://www.google.com/search?q=菜名&tbm=isch)`
*(注意：q=后面直接跟菜名)*

报告结构：
<div class="report-card">
    <div class="dish-title">
        1. [菜名](https://www.google.com/search?q=菜名&tbm=isch) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <p><strong>💡 融合创意：</strong> (解释中西结合点)</p>
    <p><strong>👨‍🍳 核心做法：</strong> (简述食材与技法)</p>
</div>

<div class="report-card">
    <div class="dish-title">
        2. [菜名](https://www.google.com/search?q=菜名&tbm=isch) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <p><strong>💡 融合创意：</strong> ...</p>
    <p><strong>👨‍🍳 核心做法：</strong> ...</p>
</div>

<div class="report-card">
    <div class="dish-title">
        3. [菜名](https://www.google.com/search?q=菜名&tbm=isch) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <p><strong>💡 融合创意：</strong> ...</p>
    <p><strong>👨‍🍳 核心做法：</strong> ...</p>
</div>
"""

# --- 6. 主程序 ---

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# --- 语音输入模块 (使用新库) ---
st.markdown("---")
c1, c2 = st.columns([8, 1])
with c1:
    st.caption("👇 点击下方麦克风说话 (支持中文)")

with c2:
    # 修复点：使用新的语音组件
    # language='zh' 代表中文
    text_from_voice = speech_to_text(
        language='zh',
        start_prompt="🎙️",
        stop_prompt="⏹️",
        just_once=True,
        key='STT_NEW'
    )

# 处理输入逻辑
final_input = None

# 情况1：用户用了语音
if text_from_voice:
    final_input = text_from_voice
    st.toast(f"🎤 识别成功：{text_from_voice}")

# 情况2：用户用了键盘打字
text_input = st.chat_input("输入研发需求...")
if text_input:
    final_input = text_input

# --- 执行逻辑 ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.markdown(final_input)

    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 正在听取指令并研发..."):
                search_query = f"{final_input} 中西融合菜 创意做法 食材搭配"
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.7)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", FUSION_PROMPT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "user_input": final_input, 
                    "evidence": evidence
                })

                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"运行出错: {e}")
