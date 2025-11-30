import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Fusion",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入 CSS (更高级的黑金风格，体现中西融合的高级感)
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 15px; background: white; z-index: 999;}
    .block-container {padding-top: 2rem; padding-bottom: 10rem;} 
    h1 {color: #1A1A1A;}
    .report-card {
        background-color: #fff;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        border-left: 6px solid #CCA352; /* 黑金配色的金 */
        margin-top: 20px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
    }
    .dish-title {
        font-size: 1.4rem;
        font-weight: bold;
        color: #1A1A1A;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
    }
    .fusion-badge {
        background-color: #1A1A1A;
        color: #CCA352;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        margin-left: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .section-title {
        font-weight: bold;
        color: #CCA352;
        margin-top: 10px;
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

# --- 4. 标题与身份 ---
st.title("🍽️ 行政总厨 (Fusion Cuisine)")
st.caption("v10.0: 擅长中西食材碰撞 • 打造高溢价创意菜")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 融合灵感")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🥩 牛排的中式做法"):
            handle_quick_action("我想做一道高客单价的牛肉菜，用西式牛排的食材（如M9和牛），但要融合中式/潮汕的口味或酱汁。")
            st.rerun()
    with c2:
        if st.button("🥗 西式摆盘的潮汕菜"):
            handle_quick_action("传统的潮汕冻鱼或生腌，如何通过西餐的摆盘和配料（如鱼子酱、泡沫）来提升价值感？")
            st.rerun()

# --- 5. 核心 Prompt (中西融合版) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT = """
你是一名精通**【中西融合菜 (Fusion Cuisine)】**的行政总厨。
你深谙**法餐/意餐**的精致摆盘与食材（如黑松露、鱼子酱、芝士、迷迭香），同时精通**中餐**（特别是粤菜/潮汕菜）的底味与锅气。

用户的需求是："{user_input}"
市场情报："{evidence}"

请提供 **3个** 具体的【中西结合】菜品研发方案。

⚠️ **融合原则（必须遵守）：**
1.  **结构：** 必须是 "中式食材+西式做法" 或 "西式食材+中式调味"。
2.  **具体菜名：** 菜名要听起来很贵、很有创意。（例如：*黑松露慢煮鲍鱼*、*普宁豆酱焗波士顿龙虾*）。
3.  **视觉链接：** 菜名必须加 Google 图片链接。

报告结构：
<div class="report-card">
    <div class="dish-title">
        1. [菜名](链接) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>解释这道菜哪里中西结合了？（例如：用了法式低温慢煮处理中式狮子头）</p>
    
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>列出关键材料（如：帕玛森芝士、5J火腿）和烹饪要点。</p>
</div>

<div class="report-card">
    <div class="dish-title">
        2. [菜名](链接) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>...</p>
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>...</p>
</div>

<div class="report-card">
    <div class="dish-title">
        3. [菜名](链接) 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>...</p>
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>...</p>
</div>
"""

# --- 6. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

user_input = st.chat_input("请输入研发需求（例如：用海鲜做一道中西结合的前菜）...")

if user_input or st.session_state.get("trigger_run", False):
    if st.session_state.get("trigger_run", False):
        current_prompt = st.session_state.messages[-1]["content"]
        st.session_state.trigger_run = False
    else:
        current_prompt = user_input
        st.session_state.messages.append({"role": "user", "content": current_prompt})
        with st.chat_message("user"):
            st.markdown(current_prompt)

    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 行政总厨正在构思融合灵感..."):
                # --- 搜索逻辑：强制加上 Fusion 相关的词 ---
                search_query = f"{current_prompt} 中西融合菜 创意菜 做法 搭配 Fusion Cuisine"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                # --- 推理 ---
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.7) # 融合菜需要高创意，温度调到0.7
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", FUSION_PROMPT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "user_input": current_prompt, 
                    "evidence": evidence
                })

                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"运行出错: {e}")
