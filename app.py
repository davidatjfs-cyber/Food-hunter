import streamlit as st
import datetime
import re
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef Fusion History",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded" # 默认展开侧边栏，为了看历史
)

# --- 2. CSS 样式 (去掉了链接样式，保留黑金卡片) ---
st.markdown("""
<style>
    /* 全局字体 */
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    
    /* 底部留白 */
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
    
    /* 菜名标题 (去掉了链接颜色，改为黑金) */
    .dish-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        line-height: 1.4;
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
    
    /* 侧边栏历史记录样式 */
    .history-item {
        padding: 8px 10px;
        background: #f0f2f6;
        border-radius: 5px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #555;
        border-left: 3px solid #C5A059;
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

# --- 4. 侧边栏 (新增：历史记录列表) ---
with st.sidebar:
    st.title("⚙️ 设置 & 历史")
    
    # 1. 设置区
    with st.expander("🔑 API Key 配置"):
        if not deepseek_key:
            deepseek_key = st.text_input("DeepSeek Key", type="password")
        if not tavily_key:
            tavily_key = st.text_input("Tavily Key", type="password")
            
    if st.button("🗑️ 清空所有记录", type="primary"):
        st.session_state.messages = []
        st.rerun()
        
    st.divider()
    
    # 2. 历史提问区 (模仿 Chat 列表)
    st.subheader("📜 历史提问")
    
    # 筛选出用户的提问
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    
    if not user_msgs:
        st.caption("暂无记录")
    else:
        # 倒序显示，最新的在最上面
        for i, msg in enumerate(reversed(user_msgs)):
            # 截取前20个字作为标题
            title = msg["content"][:20] + "..." if len(msg["content"]) > 20 else msg["content"]
            st.markdown(f'<div class="history-item">{title}</div>', unsafe_allow_html=True)

# --- 5. 主界面标题 ---
st.title("👨‍🍳 行政总厨 (纯净版)")
st.caption("v17.0: 无链接 • 左侧历史记录 • 摆盘指导")

# --- 6. 核心 Prompt (去掉了链接指令) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT = """
你是一名精通**【中西融合菜】**的行政总厨。
用户需求："{user_input}"
市场情报："{evidence}"

请提供 **3个** 高溢价的研发方案。

⚠️ **格式铁律：**
1.  **纯 HTML 输出：** 不要用 ```html 包裹。
2.  **不要缩进：** 所有 HTML 标签必须顶格写。
3.  **不要加链接：** 菜名直接写文本即可，不要加 <a> 标签。

输出模板（直接输出 HTML）：
<div class="report-card">
<div class="dish-title">1. 菜名</div>
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

# --- 8. 输入框 ---
user_input = st.chat_input("输入研发需求（例如：做一道适合秋季的创意鸭肉菜）...")

# --- 执行逻辑 ---
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key")
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
                
                # 清洗代码框
                response = re.sub(r"```[a-zA-Z]*", "", response)
                response = response.replace("```", "")
                
                # 清除缩进
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
