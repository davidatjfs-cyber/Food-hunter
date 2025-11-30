import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 (保持美观的 v5 UI) ---
st.set_page_config(
    page_title="FoodHunter Classic",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 15px; background: white; z-index: 999;}
    .block-container {padding-top: 2rem; padding-bottom: 10rem;} 
    h1 {color: #D32F2F;}
    .report-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #D32F2F;
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

# --- 4. 标题 ---
st.title("🦞 餐饮情报官 (经典版)")
st.caption("回归初心：最直接的搜索，最真实的反馈")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 经典指令")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 本月爆款拆解"):
            handle_quick_action("最近一个月上海餐饮市场最火的爆款单品是什么？")
            st.rerun()
    with c2:
        if st.button("👀 竞对差评分析"):
            handle_quick_action("帮我搜一下上海大宁久光附近的粤菜馆，看看顾客差评主要集中在哪？")
            st.rerun()

# --- 5. 核心逻辑 (回归最原始、最有效的 Prompt) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

# 这里去掉了复杂的指令，让 AI 自由发挥，反而往往效果最好
CLASSIC_PROMPT = """
你是一名餐饮研发总监。
请根据下面的【搜索结果】，回答老板的问题。

要求：
1. **重点突出：** 发现什么就说什么，不要废话。
2. **图文结合：** 遇到具体的菜名，请给出 Google 图片链接，格式为：[菜名](https://www.google.com/search?tbm=isch&q=菜名)。

报告结构：
<div class="report-card">
<h3>📊 分析报告</h3>
(你的分析内容)
</div>

---
**参考资料：** {evidence}
"""

# --- 6. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

user_input = st.chat_input("输入您的问题...")

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
            with st.spinner("🚀 正在搜索..."):
                # --- 回归经典搜索逻辑 ---
                # 不做复杂的改写，直接把你说的词加上“最新”两个字扔给搜索引擎
                # 这种方式最简单粗暴，但往往最不会出错
                search_query = f"{current_prompt} 最新 餐饮趋势"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                # --- 推理 ---
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.6)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", CLASSIC_PROMPT),
                    ("user", "问题: {input}\n\n搜索结果: {evidence}")
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "input": current_prompt, 
                    "evidence": evidence
                })

                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"运行出错: {e}")
