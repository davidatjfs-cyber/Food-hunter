import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from streamlit_mic_recorder import speech_to_text

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Ultimate",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. 深度 CSS 优化 (解决话筒和链接问题) ---
st.markdown("""
<style>
    /* 全局字体与颜色 */
    h1 {color: #BF360C;}
    
    /* 报告卡片样式 */
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #eee;
        border-left: 6px solid #BF360C; /* 深橙色 */
        margin-top: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    /* 强制链接样式 (解决链接不能点的问题) */
    a.dish-link {
        color: #1565C0 !important; /* 鲜艳的蓝色 */
        font-weight: bold;
        text-decoration: underline;
        font-size: 1.1em;
        cursor: pointer;
    }
    a.dish-link:hover {
        color: #0D47A1 !important;
        background-color: #E3F2FD;
    }

    /* 标签样式 */
    .tag-chinese { background: #FFEBEE; color: #C62828; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .tag-fusion { background: #E3F2FD; color: #1565C0; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .tag-creative { background: #E8F5E9; color: #2E7D32; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }

    /* 调整底部空间，防止输入框挡住内容 */
    .block-container {padding-bottom: 140px;}
    
    /* 调整输入框位置 */
    .stChatInput {
        z-index: 1000;
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
    
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# --- 5. 标题 ---
st.title("👨‍🍳 全能行政总厨 (v12.0)")
st.caption("中餐升级 • 中西融合 • 时令创意")

# --- 6. 核心 Prompt (结构大调整：3种方向) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

CHEF_PROMPT = """
你是一名拥有20年经验的【行政总厨】，精通**粤菜/潮汕菜**，同时深谙**西式烹饪技法**。
用户需求："{user_input}"
市场情报："{evidence}"

请提供 **3个** 不同维度的研发方案，必须包含以下三类：

1.  **【极致中餐 (Classic Upgrade)】**：在传统做法上，通过食材升级或细节微调，提升价值感。（例如：用30年的陈皮做红豆沙，或者用泉水炖汤）。
2.  **【中西融合 (East Meets West)】**：结合西式食材（黑松露、芝士、黄油）或技法（慢煮、炙烤），但保留中餐底味。
3.  **【时令/创意 (Seasonal Creative)】**：当下最流行的吃法或摆盘。

⚠️ **强制链接规则（使用 HTML）：**
必须将菜名包装成 HTML 链接，格式如下：
`<a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a>`

报告结构（直接输出 HTML）：
<div class="report-card">
    <div><span class="tag-chinese">方向1：极致中餐</span></div>
    <h3>1. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a></h3>
    <p><strong>💡 升级点：</strong> ...</p>
    <p><strong>👨‍🍳 做法精髓：</strong> ...</p>
</div>

<div class="report-card">
    <div><span class="tag-fusion">方向2：中西融合</span></div>
    <h3>2. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a></h3>
    <p><strong>💡 融合点：</strong> ...</p>
    <p><strong>👨‍🍳 做法精髓：</strong> ...</p>
</div>

<div class="report-card">
    <div><span class="tag-creative">方向3：时令创意</span></div>
    <h3>3. <a href="https://www.google.com/search?q=菜名&tbm=isch" class="dish-link" target="_blank">菜名</a></h3>
    <p><strong>💡 创意点：</strong> ...</p>
    <p><strong>👨‍🍳 做法精髓：</strong> ...</p>
</div>
"""

# --- 7. 主逻辑 ---

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# --- 8. 交互区域 (话筒 + 输入框优化) ---
# 使用 container 将话筒放在更靠近底部的位置
st.markdown("<br>", unsafe_allow_html=True) # 占位
action_container = st.container()

with action_container:
    # 布局：左侧提示文字，右侧放话筒
    c1, c2 = st.columns([0.85, 0.15]) 
    with c1:
        st.caption("👇 点击右侧话筒说话，或在下方打字")
    with c2:
        # 语音按钮
        text_from_voice = speech_to_text(
            language='zh',
            start_prompt="🎙️",
            stop_prompt="⏹️",
            just_once=True,
            key='STT_V12'
        )

# 处理输入
final_input = None

if text_from_voice:
    final_input = text_from_voice
    st.toast(f"🎤 识别内容：{text_from_voice}")

text_input = st.chat_input("输入研发需求（例如：想做一道高客单价的虾蟹菜）...")
if text_input:
    final_input = text_input

# --- 执行逻辑 ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.markdown(final_input)

    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key，请在侧边栏设置中配置。")
        st.stop()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("👨‍🍳 总厨正在规划中西餐单..."):
                # 搜索策略：同时覆盖中餐传统做法和西餐创新
                search_query = f"{final_input} 高端做法 传统技法 创意摆盘 融合菜 流行趋势"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.6)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", CHEF_PROMPT),
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
