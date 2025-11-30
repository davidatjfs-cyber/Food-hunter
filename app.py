import streamlit as st
import datetime
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

# --- 2. 深度 CSS 优化 (黑金高端风 + 强制链接修复) ---
st.markdown("""
<style>
    /* 全局颜色 */
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    
    /* 底部输入框背景优化 */
    .stChatInput {
        position: fixed; 
        bottom: 0; 
        background: rgba(255, 255, 255, 0.95); 
        padding-bottom: 20px; 
        padding-top: 10px;
        z-index: 999;
        border-top: 1px solid #eee;
    }
    
    /* 增加底部留白，防止内容被输入框挡住 */
    .block-container {padding-bottom: 150px;}
    
    /* 报告卡片：黑金风格 */
    .report-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #f0f0f0;
        border-left: 5px solid #C5A059; /* 香槟金 */
        margin-top: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    
    /* 菜名标题 */
    .dish-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
    }
    
    /* 核心修复：强制链接样式 */
    .dish-link {
        color: #0056b3 !important; /* 经典的链接蓝，确保可见 */
        text-decoration: underline !important;
        cursor: pointer;
        margin-right: 8px;
    }
    
    /* 小标签样式 */
    .fusion-badge {
        background-color: #1A1A1A;
        color: #C5A059;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        white-space: nowrap;
    }
    
    /* 段落标题 */
    .section-title {
        font-size: 0.95rem;
        font-weight: bold;
        color: #C5A059;
        margin-top: 12px;
        margin-bottom: 4px;
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
    
    # 清空历史按钮
    if st.button("🗑️ 清空聊天记录", type="secondary"):
        st.session_state.messages = []
        st.rerun()

# --- 5. 标题 ---
st.title("👨‍🍳 行政总厨 (Fusion Pro)")
st.caption("v13.0: 链接修复 • 支持下载 • 界面精修")

# 快捷指令
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

# --- 6. 核心 Prompt (v10.0逻辑 + HTML链接强制) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT = """
你是一名精通**【中西融合菜 (Fusion Cuisine)】**的行政总厨。
你深谙**法餐/意餐**的精致摆盘与食材（如黑松露、鱼子酱、芝士、迷迭香），同时精通**中餐**（特别是粤菜/潮汕菜）的底味与锅气。

用户的需求是："{user_input}"
市场情报："{evidence}"

请提供 **3个** 具体的【中西结合】菜品研发方案。

⚠️ **重要：链接格式修正**
必须使用 **HTML <a> 标签** 来生成链接，确保能在新窗口打开。
格式：`<a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a>`

报告结构（直接输出 HTML）：
<div class="report-card">
    <div class="dish-title">
        1. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a> 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>解释这道菜哪里中西结合了？</p>
    
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>列出关键材料和烹饪要点。</p>
</div>

<div class="report-card">
    <div class="dish-title">
        2. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a> 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>...</p>
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>...</p>
</div>

<div class="report-card">
    <div class="dish-title">
        3. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a> 
        <span class="fusion-badge">Fusion Idea</span>
    </div>
    <div class="section-title">💡 中西碰撞点 (The Twist)</div>
    <p>...</p>
    <div class="section-title">👨‍🍳 核心食材与技法</div>
    <p>...</p>
</div>
"""

# --- 7. 主程序 ---

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# 输入框
user_input = st.chat_input("请输入研发需求（例如：用海鲜做一道中西结合的前菜）...")

# 逻辑处理
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
        st.error("❌ 未检测到 API Key，请在侧边栏配置")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 行政总厨正在构思融合灵感..."):
                # 搜索逻辑：v10.0 的逻辑，加上 Fusion 词汇
                search_query = f"{current_prompt} 中西融合菜 创意菜 做法 搭配 Fusion Cuisine"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.7)
                
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
                
                # --- 新增功能：下载保存 ---
                # 获取当前时间生成文件名
                now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
                st.download_button(
                    label="📥 下载这份研发报告",
                    data=response,
                    file_name=f"研发方案_{now_str}.html",
                    mime="text/html"
                )

        except Exception as e:
            st.error(f"运行出错: {e}")
