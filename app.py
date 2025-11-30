import streamlit as st
import datetime
import re
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef R&D Pure",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 样式 (纯净版，无图片样式) ---
st.markdown("""
<style>
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    .block-container {padding-bottom: 100px;}
    
    /* 报告卡片：深红中式风格 */
    .report-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        border-left: 6px solid #B71C1C; /* 中国红 */
        margin-top: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    
    .dish-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        line-height: 1.4;
    }
    
    /* 章节标题 */
    h4 {
        color: #B71C1C !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        margin-top: 25px !important;
        margin-bottom: 10px !important;
        background: #FFEBEE;
        padding: 5px 10px;
        border-radius: 4px;
        display: inline-block;
    }
    
    p, li {
        font-size: 1rem;
        line-height: 1.6;
        color: #333;
        margin-bottom: 8px;
    }

    /* SOP 步骤样式 */
    .step-box {
        background: #FAFAFA;
        padding: 15px;
        border-radius: 8px;
        border: 1px dashed #ccc;
    }
    .step-item {
        margin-bottom: 8px; 
        padding-left: 10px;
        border-left: 3px solid #ddd;
    }
    
    .history-item {
        padding: 8px 10px;
        background: #f0f2f6;
        border-radius: 5px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #555;
        border-left: 3px solid #B71C1C;
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

# --- 4. 辅助函数：将 HTML 转为纯文本供复制 ---
def clean_html_for_copy(html_text):
    """
    把漂亮的 HTML 转换成适合复制到微信的纯文本
    """
    # 替换标题
    text = html_text.replace("<h4>", "\n【").replace("</h4>", "】\n")
    text = text.replace('<div class="dish-title">', "\n===============\n🍲 ").replace("</div>", "\n===============\n")
    text = text.replace("<strong>", "").replace("</strong>", "")
    text = text.replace('<div class="step-item">', "👉 ").replace("</div>", "")
    
    # 去掉剩余标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 调整空行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("📜 研发历史")
    st.divider()
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if not user_msgs:
        st.caption("暂无记录")
    else:
        for i, msg in enumerate(reversed(user_msgs)):
            title = msg["content"][:20] + "..." if len(msg["content"]) > 20 else msg["content"]
            st.markdown(f'<div class="history-item">{title}</div>', unsafe_allow_html=True)
    st.divider()
    if st.button("🗑️ 清空记录"):
        st.session_state.messages = []
        st.rerun()

# --- 6. 主界面 ---
st.title("👨‍🍳 研发总监 (纯净SOP版)")
st.caption("v22.0: 无图极速 • 中式创意 • 一键复制")

# --- 7. Prompt (移除图片指令) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

RD_PROMPT_TEXT = """
你是一名拥有25年经验的**【中餐研发总监】**，精通潮汕菜、粤菜。
你的设计风格是：**"中魂西技"**（Chinese Soul, Modern Presentation）。

用户需求："{user_input}"
市场情报："{evidence}"

请设计 **3道** 高溢价的创意菜品，方向如下：
1.  **【新中式·意境菜】**
2.  **【中西·高定融合】**
3.  **【功夫·位上菜】**

⚠️ **格式铁律：**
1.  **纯 HTML 输出**，顶格写，不要缩进，不要 ```html。
2.  **不要图片，不要链接**。
3.  **内容详实：** 必须包含【精准食材】和【SOP步骤】。

输出模板（HTML）：
<div class="report-card">
<div class="dish-title">1. 菜名1</div>
<p><strong>💡 研发理念：</strong>...</p>

<h4>🥩 精准食材 (Ingredients)</h4>
<p>
<strong>主料：</strong>...<br>
<strong>辅料：</strong>...<br>
<strong>关键调味：</strong>...
</p>

<h4>🔥 落地步骤 (SOP)</h4>
<div class="step-box">
<div class="step-item"><strong>Step 1 (预处理)：</strong>...</div>
<div class="step-item"><strong>Step 2 (烹饪/火候)：</strong>...</div>
<div class="step-item"><strong>Step 3 (调味/收汁)：</strong>...</div>
</div>

<h4>🎨 摆盘美学 (Plating)</h4>
<p><strong>器皿建议：</strong>...</p>
<p><strong>装饰：</strong>...</p>
</div>

(请重复3次，分别对应三个方案)
"""

# --- 8. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # 渲染漂亮的 HTML 卡片
            st.markdown(msg["content"], unsafe_allow_html=True)
            
            # --- 生成“复制框” ---
            # 如果是 AI 的回复，就在下面加一个复制框
            # 只有当内容包含 "report-card" 时才显示（避免把报错信息也弄成复制框）
            if "report-card" in msg["content"]:
                clean_text = clean_html_for_copy(msg["content"])
                with st.expander("📝 点击复制纯文本 (用于发微信/文档)"):
                    st.code(clean_text, language=None)

        else:
            st.markdown(msg["content"])

user_input = st.chat_input("输入研发需求（例如：想做一道用花胶为主料的创意前菜）...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not deepseek_key or not tavily_key:
        st.error("❌ Key 缺失")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 总厨正在拆解SOP步骤..."):
                search_query = f"{user_input} 高端中餐 创意菜 做法食谱 详细配方plating"
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.6)
                chain = ChatPromptTemplate.from_messages([
                    ("system", RD_PROMPT_TEXT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                text_response = chain.invoke({"user_input": user_input, "evidence": evidence})
                
                # 清洗代码
                text_response = re.sub(r"```[a-zA-Z]*", "", text_response).replace("```", "")
                cleaned_lines = [line.strip() for line in text_response.split('\n')]
                text_response = "\n".join(cleaned_lines)

            # 显示漂亮的卡片
            placeholder.markdown(text_response, unsafe_allow_html=True)
            
            # 保存到历史
            st.session_state.messages.append({"role": "assistant", "content": text_response})
            
            # 立即显示复制框
            clean_text = clean_html_for_copy(text_response)
            with st.expander("📝 点击复制纯文本 (用于发微信/文档)", expanded=True):
                st.code(clean_text, language=None)

        except Exception as e:
            st.error(f"运行出错: {e}")
