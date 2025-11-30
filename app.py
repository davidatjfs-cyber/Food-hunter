import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面美化配置 ---
st.set_page_config(
    page_title="FoodHunter Pro",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起侧边栏，手机看更宽敞
)

# 注入自定义 CSS，让界面更像 App
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 15px; background: white; z-index: 999;}
    .block-container {padding-top: 2rem; padding-bottom: 10rem;} 
    h1 {color: #D32F2F; font-size: 1.8rem;}
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        border: 1px solid #ff4b4b;
        color: #ff4b4b;
        background-color: white;
    }
    .stButton>button:hover {
        background-color: #ff4b4b;
        color: white;
    }
    .report-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #D32F2F;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 核心逻辑与密钥 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. 侧边栏 (隐藏式) ---
with st.sidebar:
    st.title("⚙️ 设置")
    
    # 把 Key 的输入藏在折叠框里
    with st.expander("🔑 API Key 配置"):
        if not deepseek_key:
            deepseek_key = st.text_input("DeepSeek Key", type="password")
        if not tavily_key:
            tavily_key = st.text_input("Tavily Key", type="password")
            
    if st.button("🗑️ 清空聊天记录", type="primary"):
        st.session_state.messages = []
        st.rerun()
    
    st.info("💡 提示：点击左上角的小箭头可以收起本菜单")

# --- 4. 标题区 ---
st.title("🦞 餐饮情报官")
st.caption("您的 24小时 AI 研发总监 • 实时挖掘全网趋势")

# --- 5. 快捷指令区 (新增核心功能) ---
# 定义处理函数
def handle_quick_action(prompt_text):
    # 把问题直接加到输入框逻辑里
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    # 强制标记需要运行
    st.session_state.trigger_run = True

# 只有当历史记录为空时，才显示快捷按钮（避免刷屏）
if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 想要查什么？")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🍲 本月爆款拆解"):
            handle_quick_action("帮我搜一下最近一个月上海餐饮市场最火的爆款单品是什么？分析它的口味和卖点。")
            st.rerun()
        if st.button("📝 朋友圈文案"):
            handle_quick_action("我要发朋友圈宣传我的餐厅（主打潮汕菜/粤菜），帮我写3条吸引人的文案，要带emoji，适合下雨天/周末发。")
            st.rerun()
    with col2:
        if st.button("👀 竞对差评分析"):
            handle_quick_action("帮我搜一下上海大宁久光附近的粤菜馆，看看顾客最近的差评主要集中在哪里？我要避坑。")
            st.rerun()
        if st.button("💡 冬季新品灵感"):
            handle_quick_action("适合冬天的、高利润的、有仪式感的粤菜或潮汕菜新品有哪些？给我推荐3个。")
            st.rerun()

# --- 6. 聊天主逻辑 ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

TREND_HUNTER_PROMPT = """
你是一名餐饮专家。今天是：{current_date}。
请输出 Markdown 格式报告，风格要简洁、专业、口语化。

报告结构：
<div class="report-card">
<h3>📊 市场情报摘要</h3>
[一句话核心结论]

<h4>1. 🕵️‍♂️ 趋势/爆款分析</h4>
[内容]

<h4>2. 💡 给老板的建议</h4>
[内容]

</div>

---
**来源：** {evidence}
"""

# 显示历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # 如果是 AI 回复，允许渲染 HTML (为了上面的卡片样式)
        if message["role"] == "assistant":
            st.markdown(message["content"], unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# 处理输入 (手动输入 or 按钮触发)
user_input = st.chat_input("输入您的问题...")

# 逻辑判断：如果有手动输入 OR 有快捷按钮触发
if user_input or st.session_state.get("trigger_run", False):
    
    # 如果是按钮触发的，user_input 可能是空的，要从历史最后一条取
    if st.session_state.get("trigger_run", False):
        current_prompt = st.session_state.messages[-1]["content"]
        st.session_state.trigger_run = False # 重置开关
    else:
        current_prompt = user_input
        # 手动输入的要先显示并存历史
        st.session_state.messages.append({"role": "user", "content": current_prompt})
        with st.chat_message("user"):
            st.markdown(current_prompt)

    # 检查 Key
    if not deepseek_key or not tavily_key:
        st.error("请先在左上角设置里配置 API Key")
        st.stop()

    # AI 生成
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("🦞 正在全网打捞情报..."):
                now = datetime.datetime.now()
                # 搜索
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                # 强制加上时间
                query = f"{current_prompt} {now.strftime('%Y年%m月')} 最新"
                evidence = search.invoke(query)
                
                # 推理
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.6)
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "需求: {input}\n\n情报: {evidence}")
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "input": current_prompt, 
                    "evidence": evidence,
                    "current_date": now.strftime("%Y-%m-%d")
                })
                
                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # 下载按钮
                file_name = f"餐饮情报_{now.strftime('%H%M')}.md"
                st.download_button("💾 下载报告", response, file_name)
                
        except Exception as e:
            st.error(f"出错: {e}")
