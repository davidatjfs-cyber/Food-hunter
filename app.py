import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter R&D",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 15px; background: white; z-index: 999;}
    .block-container {padding-top: 2rem; padding-bottom: 10rem;} 
    h1 {color: #E65100;} /* 换成更有食欲的橙色 */
    .report-card {
        background-color: #fff;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #eee;
        border-left: 6px solid #E65100;
        margin-top: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .dish-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #E65100;
        margin-bottom: 10px;
    }
    .tag {
        background-color: #FFF3E0;
        color: #E65100;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8rem;
        margin-right: 5px;
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

# --- 4. 标题与身份定义 ---
st.title("👨‍🍳 餐饮研发总监 (R&D Director)")
st.caption("v9.0: 精通食材与烹饪 • 结合市场趋势提供研发方案")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 研发方向")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 冬季滋补菜研发"):
            handle_quick_action("我想开发几道适合冬天的滋补菜，要用牛羊肉，但做法要新颖，不要老一套。")
            st.rerun()
    with c2:
        if st.button("🦐 潮汕菜微创新"):
            handle_quick_action("我是做潮汕菜的，想在这个基础上结合现在的流行趋势做点微创新，有什么具体菜品建议？")
            st.rerun()

# --- 5. 核心 Prompt (角色大变身) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

RD_PROMPT = """
你是一名拥有20年经验的【餐饮研发总监】兼【行政总厨】。
你精通中西餐各种食材特性、烹饪技法（如低温慢煮、啫啫、生腌、分子料理等）以及风味搭配逻辑。

用户的需求是："{user_input}"
搜索到的市场情报是："{evidence}"

请结合市场情报和你专业的烹饪知识，提供 **3个** 具体的菜品研发建议。

⚠️ **输出要求：**
1.  **具体菜名**：必须是具体的、可落地的菜名，不要笼统的类别。
2.  **研发思路**：一句话解释为什么要推这道菜（结合了什么流行趋势？解决了什么痛点？）。
3.  **烹饪/食材亮点**：**这是你发挥专家能力的地方。** 请指出这道菜的关键食材、特殊调味或创新技法。（例如：用了什么特殊的酱汁？加了什么意想不到的辅料？）
4.  **视觉链接**：给菜名加上 Google 图片链接。

报告结构：
<div class="report-card">
    <div class="dish-title">1. [菜名](链接) <span class="tag">推荐指数⭐⭐⭐⭐⭐</span></div>
    <p><strong>💡 研发思路：</strong> ...</p>
    <p><strong>👨‍🍳 烹饪/食材亮点：</strong> ...</p>
</div>

<div class="report-card">
    <div class="dish-title">2. [菜名](链接) <span class="tag">推荐指数⭐⭐⭐⭐</span></div>
    <p><strong>💡 研发思路：</strong> ...</p>
    <p><strong>👨‍🍳 烹饪/食材亮点：</strong> ...</p>
</div>

<div class="report-card">
    <div class="dish-title">3. [菜名](链接) <span class="tag">推荐指数⭐⭐⭐⭐</span></div>
    <p><strong>💡 研发思路：</strong> ...</p>
    <p><strong>👨‍🍳 烹饪/食材亮点：</strong> ...</p>
</div>
"""

# --- 6. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

user_input = st.chat_input("请输入您的研发方向（如：想做一道有仪式感的鸡肉菜）...")

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
            with st.spinner("👨‍🍳 研发总监正在拆解风味与技法..."):
                # --- 搜索逻辑：不仅搜名字，还要搜“做法”和“创新” ---
                # 这样才能保证 AI 拿到的是“有技术含量”的信息
                search_query = f"{current_prompt} 创新做法 流行吃法 独特食材搭配 爆款菜单"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                # --- 推理 ---
                # 温度稍微调高一点(0.5)，让大厨在烹饪组合上有点创意，但不要太离谱
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.5)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", RD_PROMPT),
                    ("user", "") # Prompt里已经包含了 user_input，这里留空即可
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "user_input": current_prompt, 
                    "evidence": evidence
                })

                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            st.error(f"运行出错: {e}")
