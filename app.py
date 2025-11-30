import streamlit as st
import datetime
import re # 引入正则库，专门处理乱码
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from streamlit_mic_recorder import speech_to_text

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef Fusion Pro",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. 深度 CSS 优化 ---
st.markdown("""
<style>
    /* 全局字体 */
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    
    /* 输入框固定底部 */
    .stChatInput {
        position: fixed; 
        bottom: 0; 
        background: rgba(255, 255, 255, 0.98); 
        padding-bottom: 20px; 
        padding-top: 10px;
        z-index: 999;
        border-top: 1px solid #eee;
    }
    .block-container {padding-bottom: 160px;}
    
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
    }
    
    /* 强制链接样式 */
    .dish-link {
        color: #0056b3 !important;
        text-decoration: underline !important;
        cursor: pointer;
    }
    
    /* 核心章节标题 (H4) */
    h4 {
        color: #C5A059 !important; /* 金色标题 */
        font-size: 1.05rem !important;
        font-weight: bold !important;
        margin-top: 15px !important;
        margin-bottom: 5px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* 正文文字 */
    p, li {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #444;
        margin-bottom: 8px;
    }
    
    /* 摆盘美学高亮块 */
    .plating-box {
        background-color: #F9F9F9;
        border-radius: 8px;
        padding: 10px 15px;
        border-left: 3px solid #333;
        margin-top: 10px;
        font-style: italic;
        color: #555;
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
st.title("👨‍🍳 行政总厨 (视觉美学版)")
st.caption("v14.0: 修复乱码 • 增加摆盘指导 • 链接直达")

# --- 6. 核心 Prompt (简化HTML结构，防止AI出错) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

# 这里我们将指令改得更简单，用标准 H4 标签，AI 不容易出错
FUSION_PROMPT = """
你是一名精通**【中西融合菜】**的行政总厨。
用户需求："{user_input}"
市场情报："{evidence}"

请提供 **3个** 高溢价的研发方案。

⚠️ **格式铁律（违反会导致系统崩溃）：**
1.  **纯 HTML 输出：** 不要用 Markdown 代码块包裹（严禁使用 ```html 或 ```）。
2.  **链接格式：** `<a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a>`
3.  **摆盘美学：** 每个方案必须包含【摆盘指导】，描述器皿选择、堆叠方式、酱汁划盘、装饰物。

输出模板（请严格照抄结构）：
<div class="report-card">
    <div class="dish-title">
        1. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a>
    </div>
    
    <h4>💡 中西融合灵感</h4>
    <p>解释融合点...</p>
    
    <h4>👨‍🍳 核心食材与技法</h4>
    <p>列出关键材料和步骤...</p>
    
    <h4>🎨 摆盘美学 (Plating)</h4>
    <div class="plating-box">
        <p><strong>器皿：</strong>黑岩板 / 白瓷草帽盘 / 复古铜盘...</p>
        <p><strong>构图：</strong>...描述如何摆放...</p>
    </div>
</div>

(请重复3次，分别对应三个方案)
"""

# --- 7. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# --- 8. 交互区域 ---
st.markdown("<br>", unsafe_allow_html=True)
action_container = st.container()

with action_container:
    c1, c2 = st.columns([0.85, 0.15]) 
    with c1:
        st.caption("👇 点击右侧话筒说话，或在下方打字")
    with c2:
        text_from_voice = speech_to_text(
            language='zh',
            start_prompt="🎙️",
            stop_prompt="⏹️",
            just_once=True,
            key='STT_V14'
        )

final_input = None
if text_from_voice:
    final_input = text_from_voice
    st.toast(f"🎤 识别内容：{text_from_voice}")

text_input = st.chat_input("输入研发需求（例如：想做一道带烟熏味的牛肉前菜）...")
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
            with st.spinner("👨‍🍳 总厨正在设计摆盘..."):
                search_query = f"{final_input} 高端摆盘 中西融合菜 做法 创意 French plating"
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
                
                # --- 🔥 强力清洗代码 (Regex Cleaning) ---
                # 无论 AI 输出什么乱七八糟的代码块，全部用正则清理掉
                # 去掉 ```html, ```xml, ``` 等
                response = re.sub(r"```[a-zA-Z]*", "", response) 
                response = response.replace("```", "").strip()

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
