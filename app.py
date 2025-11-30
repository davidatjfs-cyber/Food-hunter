import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置与美化 ---
st.set_page_config(
    page_title="FoodHunter Pro",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起侧边栏，专注内容
)

# 注入 CSS 样式：底部输入框固定、卡片样式、按钮美化
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
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff4b4b;
        color: white;
        border: 1px solid #ff4b4b;
    }
    /* 报告卡片样式 */
    .report-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #D32F2F;
        margin-top: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .report-card h3 { color: #2c3e50; font-size: 1.2rem; margin-bottom: 1rem;}
    .report-card h4 { color: #D32F2F; font-size: 1.1rem; margin-top: 1.2rem;}
</style>
""", unsafe_allow_html=True)

# --- 2. 密钥管理逻辑 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

# 初始化历史记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. 侧边栏设置 (隐藏式) ---
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
        
    st.caption("v5.0 视觉增强版")

# --- 4. 主界面标题 ---
st.title("🦞 餐饮情报官")
st.caption("您的 24小时 AI 研发总监 • 点击菜名即可看图")

# --- 5. 快捷指令区 ---
def handle_quick_action(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.session_state.trigger_run = True

# 仅当没有历史消息时显示快捷按钮
if len(st.session_state.messages) == 0:
    st.markdown("### 🔥 想要查什么？")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍲 本月爆款拆解"):
            handle_quick_action("帮我搜一下最近一个月上海餐饮市场最火的爆款单品是什么？分析它的口味和卖点。")
            st.rerun()
        if st.button("📝 朋友圈文案"):
            handle_quick_action("我要发朋友圈宣传我的餐厅（主打潮汕菜/粤菜），帮我写3条吸引人的文案，要带emoji，适合下雨天/周末发。")
            st.rerun()
    with c2:
        if st.button("👀 竞对差评分析"):
            handle_quick_action("帮我搜一下上海大宁久光附近的粤菜馆，看看顾客最近的差评主要集中在哪里？我要避坑。")
            st.rerun()
        if st.button("💡 冬季新品灵感"):
            handle_quick_action("适合冬天的、高利润的、有仪式感的粤菜或潮汕菜新品有哪些？给我推荐3个。")
            st.rerun()

# --- 6. 核心 Prompt (视觉增强版) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

TREND_HUNTER_PROMPT = """
你是一名拥有15年经验的【餐饮研发总监】。今天是：{current_date}。
请输出 Markdown 格式报告。

⚠️ **视觉增强指令 (重要)：**
当你在报告中提到任何具体的【菜品名称】、【食材】或【品牌名】时，
必须将其格式化为 **"Google 图片搜索链接"**。
格式要求：[菜品名称](https://www.google.com/search?tbm=isch&q=菜品名称)

*示例：不要只写"脆皮五花肉"，要写 [脆皮五花肉](https://www.google.com/search?tbm=isch&q=脆皮五花肉)*

报告结构如下 (请保持 HTML 标签以应用卡片样式)：
<div class="report-card">
<h3>📊 市场情报摘要</h3>
(一句话总结核心趋势)

<h4>1. 🕵️‍♂️ 趋势/爆款分析</h4>
(详细分析，记得给菜名加链接)

<h4>2. 💡 给老板的落地建议</h4>
(新品或营销建议)

</div>

---
**数据来源：** {evidence}
"""

# --- 7. 聊天主逻辑 ---

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True) # 允许渲染 HTML 卡片
        else:
            st.markdown(msg["content"])

# 处理用户输入
user_input = st.chat_input("输入您的问题...")

# 触发逻辑：手动输入 或 按钮触发
if user_input or st.session_state.get("trigger_run", False):
    
    # 获取当前问题文本
    if st.session_state.get("trigger_run", False):
        current_prompt = st.session_state.messages[-1]["content"]
        st.session_state.trigger_run = False
    else:
        current_prompt = user_input
        st.session_state.messages.append({"role": "user", "content": current_prompt})
        with st.chat_message("user"):
            st.markdown(current_prompt)

    # 检查 Key
    if not deepseek_key or not tavily_key:
        st.error("❌ 未检测到 API Key，请在侧边栏设置中配置。")
        st.stop()

    # AI 生成
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("🦞 正在全网打捞情报..."):
                now = datetime.datetime.now()
                
                # 1. 搜索 (强制带上时间)
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                query = f"{current_prompt} {now.strftime('%Y年%m月')} 最新"
                evidence = search.invoke(query)
                
                # 2. 推理
                llm = ChatOpenAI(
                    base_url=base_url, 
                    api_key=deepseek_key, 
                    model=model_name, 
                    temperature=0.6
                )
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "需求: {input}\n\n情报: {evidence}")
                ]) | llm | StrOutputParser()
                
                response = chain.invoke({
                    "input": current_prompt, 
                    "evidence": evidence,
                    "current_date": now.strftime("%Y-%m-%d")
                })
                
                # 3. 显示结果
                placeholder.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # 4. 下载按钮
                file_name = f"餐饮情报_{now.strftime('%H%M')}.md"
                st.download_button("💾 下载报告", response, file_name)
                
        except Exception as e:
            st.error(f"运行出错: {e}")
