import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Precision",
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

# --- 4. 标题与快捷区 ---
st.title("🦞 餐饮情报官 (精准版)")
st.caption("v6.0: 包含源数据透明展示，拒绝胡编乱造")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 常用指令")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 本月爆款拆解"):
            handle_quick_action("帮我搜一下最近一个月上海餐饮市场最火的爆款单品是什么？")
            st.rerun()
    with c2:
        if st.button("👀 竞对差评分析"):
            handle_quick_action("帮我搜一下上海大宁久光附近的粤菜馆，看看顾客差评主要集中在哪？")
            st.rerun()

# --- 5. 核心 Prompt (回归理性，防胡编) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

TREND_HUNTER_PROMPT = """
你是一名客观的【餐饮数据分析师】。今天是：{current_date}。

你的任务是：**基于提供的【搜索情报】，回答老板的问题。**

⚠️ **重要原则：**
1. **实事求是：** 只有搜索结果里提到的才写，**不要动用你自己的想象力去编造**。
2. **如果没有数据：** 如果搜索结果里没有相关信息，请直接回答：“抱歉，根据目前的搜索结果，没有找到相关数据。”
3. **视觉链接（适度）：** 仅为核心菜名添加 Google 图片链接。格式：[菜名](https://www.google.com/search?tbm=isch&q=菜名)

报告结构：
<div class="report-card">
<h3>📊 深度分析报告</h3>

<h4>1. 🕵️‍♂️ 关键发现</h4>
(基于证据的分析)

<h4>2. 💡 经营建议</h4>
(基于发现的推导)

</div>
"""

# --- 6. 主逻辑 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
            # 如果历史消息里存了 raw_evidence，也显示出来（可选，这里为了简洁先不显示历史的源数据）
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
            with st.spinner("🕵️‍♂️ 正在交叉验证数据源..."):
                now = datetime.datetime.now()
                
                # --- 改进搜索策略 ---
                # 不再强行加“最新”，而是让搜索词更自然，防止搜不到东西
                # 比如：把 "上海烧鹅 最新" 改为 "上海 烧鹅 评价 推荐"
                search_query = f"{current_prompt} 餐饮 美食 评价"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=6) # 增加到6条
                evidence = search.invoke(search_query)
                
                # --- 关键改动：显示搜到了什么 (Debug模式) ---
                # 这就像让厨师把买回来的菜展示给老板看，证明食材新不新鲜
                with st.expander("🔍 [透明模式] 点击查看 AI 到底搜到了什么？", expanded=False):
                    st.write(f"**实际搜索词：** `{search_query}`")
                    st.write("**搜索结果原始数据：**")
                    for item in evidence:
                        st.markdown(f"- **[{item['url']}]({item['url']})**: {item['content'][:100]}...")

                # 推理
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.3) # 温度调低，更理性
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "用户问题: {input}\n\n搜索情报(Evidence): {evidence}")
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "input": current_prompt, 
                    "evidence": evidence,
                    "current_date": now.strftime("%Y-%m-%d")
                })
                
                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
        except Exception as e:
            st.error(f"运行出错: {e}")
