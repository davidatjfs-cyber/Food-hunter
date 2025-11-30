import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Pro",
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

# 初始化 Session
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
st.title("🦞 餐饮情报官 (智能搜索版)")
st.caption("v7.0: 自动优化搜索词，解决答非所问")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 试一试")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 本月爆款拆解"):
            handle_quick_action("帮我搜一下最近一个月上海餐饮市场最火的爆款单品是什么？")
            st.rerun()
    with c2:
        if st.button("👀 竞对差评分析"):
            handle_quick_action("帮我搜一下上海大宁久光附近的粤菜馆，看看顾客差评主要集中在哪？")
            st.rerun()

# --- 5. 核心逻辑：两步走 (先生成搜索词 -> 再生成报告) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

# A. 搜索词优化专家 Agent
QUERY_GEN_PROMPT = """
你是一个Google搜索专家。
用户的原始问题是："{user_input}"
今天是：{current_date}

请将这个问题转化为**一个**最适合在搜索引擎输入的关键词。
目标：找到最新的、真实的消费者评价或餐饮数据。
技巧：
1. 去掉语气词。
2. 加上具体的地域（如果用户没说，默认假设是上海）。
3. 加上"大众点评"、"小红书"、"推荐"、"避坑"等词。

**只输出优化后的搜索词，不要有任何其他废话。**
"""

# B. 报告生成专家 Agent
REPORT_PROMPT = """
你是一名餐饮数据分析师。
请基于以下的【搜索结果】，回答用户的问题："{user_input}"

⚠️ **回答原则：**
1. **直接回答：** 不要在那绕弯子，直接给出结论。
2. **基于证据：** 搜索结果里说了什么就说什么，没说就说没查到。
3. **视觉链接：** 仅给【核心菜名】加链接：[菜名](https://www.google.com/search?tbm=isch&q=菜名)。

报告结构：
<div class="report-card">
<h3>📊 核心结论</h3>
(直球回答用户的问题)

<h4>1. 🕵️‍♂️ 详细情报</h4>
(列出具体的菜品、评价或数据)

<h4>2. 💡 建议</h4>
(简短建议)
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
            now = datetime.datetime.now()
            llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.5)

            # --- 第一步：智能生成搜索词 ---
            with st.status("🧠 正在思考最佳搜索策略...", expanded=True) as status:
                gen_chain = ChatPromptTemplate.from_template(QUERY_GEN_PROMPT) | llm | StrOutputParser()
                optimized_query = gen_chain.invoke({
                    "user_input": current_prompt,
                    "current_date": now.strftime("%Y-%m-%d")
                })
                # 清理一下生成的词（去掉可能的引号）
                optimized_query = optimized_query.replace('"', '').strip()
                
                status.write(f"🔍 原始问题：{current_prompt}")
                status.write(f"✨ **优化后去搜：** `{optimized_query}`")
                
                # --- 第二步：执行搜索 ---
                status.write("正在全网检索...")
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(optimized_query)
                status.write(f"✅ 找到 {len(evidence)} 条相关情报")
                status.update(label="✅ 情报收集完毕", state="complete", expanded=False)

            # --- 第三步：生成回答 ---
            final_chain = ChatPromptTemplate.from_template(REPORT_PROMPT) | llm | StrOutputParser()
            response = final_chain.invoke({
                "user_input": current_prompt,
                "evidence": evidence
            })

            placeholder.markdown(response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"运行出错: {e}")
