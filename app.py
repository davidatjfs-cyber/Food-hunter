import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FoodHunter Dish",
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
        background-color: #fff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #eee;
        border-left: 5px solid #D32F2F;
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
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
st.title("🦞 餐饮情报官 (硬核菜品版)")
st.caption("v8.0: 专治答非所问，强制输出具体菜名")

def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 查具体的")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 本月爆款菜品"):
            handle_quick_action("最近一个月上海餐饮市场最火的具体菜品有哪些？列出名字。")
            st.rerun()
    with c2:
        if st.button("👀 竞对招牌菜"):
            handle_quick_action("帮我搜一下大宁久光附近的粤菜馆，大家最推荐的必点菜是什么？")
            st.rerun()

# --- 5. 核心 Prompt (这里加了死命令) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

DISH_HUNTER_PROMPT = """
你是一名【菜品数据采集员】。
请根据【搜索结果】，回答用户的问题。

⚠️ **最高指令（必须严格遵守）：**
1. **我要名词，不要形容词：** 用户问“有什么产品”，你必须回答具体的**菜名**（如：黑金流沙包、熟醉蟹），**严禁**回答“喜欢辣的”、“重口味”这种废话。
2. **清单体：** 直接列出菜名清单，不要写长篇大论的分析。
3. **视觉链接：** 必须给每一个【具体菜名】加上 Google 图片链接。格式：[菜名](https://www.google.com/search?tbm=isch&q=菜名)。

❌ **错误示范：**
"最近流行比较鲜美的口味，大家喜欢吃海鲜。" (这是废话，禁止输出)

✅ **正确示范：**
"最近流行的爆款菜品有：
1. **[熟醉罗氏虾](...)**：酒香浓郁，点击率极高。
2. **[避风塘炒珍宝蟹](...)**：聚餐必点。"

报告结构：
<div class="report-card">
<h3>📋 爆款菜品清单</h3>
(这里直接列出 3-5 个具体的菜名)

<h4>💡 简要备注</h4>
(这道菜为什么火？一句话解释)
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
            with st.spinner("🚀 正在搜索具体菜单..."):
                # --- 搜索逻辑修改：强制加后缀 ---
                # 无论你问什么，我都在后面加上 "必点菜 推荐菜 菜单"，逼搜索引擎找菜名
                search_query = f"{current_prompt} 必点菜 推荐菜 菜单具体名称"
                
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                # --- 推理 ---
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.3) # 温度调低，防止胡编
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", DISH_HUNTER_PROMPT),
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
