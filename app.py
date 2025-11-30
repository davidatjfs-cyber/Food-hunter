import streamlit as st
import datetime
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(page_title="FoodHunter Pro", page_icon="🦞", layout="wide")
st.title("🦞 FoodHunter: 餐饮情报官 (带历史记录版)")

# --- 2. 自动获取密钥 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

# --- 3. 初始化历史记录 (关键步骤) ---
# 如果内存里没有“messages”，就创建一个空的列表
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. 侧边栏配置 ---
with st.sidebar:
    st.header("🔑 系统配置")
    
    # 显示清除历史按钮
    if st.button("🗑️ 清空历史记录"):
        st.session_state.messages = []
        st.rerun()
        
    st.divider()
    
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek API Key", type="password")
    if not tavily_key:
        tavily_key = st.text_input("Tavily API Key", type="password")
        
    base_url = "https://api.deepseek.com"
    model_name = "deepseek-chat" 

# --- 5. 核心 Prompt ---
TREND_HUNTER_PROMPT = """
你是一名拥有15年经验的【餐饮研发总监】。
今天是：{current_date}。
核心原则：**【只关注最新趋势】**。

请根据搜索结果回答老板的需求。
如果搜索结果是1年前的旧闻，请直接忽略或标注。

请输出 Markdown 格式策划案：
# 💡 餐饮情报分析报告
### 1. 🎯 核心趋势提炼
### 2. 🍲 爆款拆解
### 3. 🛠️ 落地建议

---
**数据来源：** {evidence}
"""

# --- 6. 页面主逻辑 (聊天窗口模式) ---

# A. 先把历史记录画在屏幕上
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# B. 等待用户输入新问题
if prompt := st.chat_input("你想了解什么餐饮情报？(例如：上海最近火锅流行什么？)"):
    
    # 1. 检查 Key
    if not deepseek_key or not tavily_key:
        st.error("❌ 请先配置 API Key")
        st.stop()

    # 2. 显示用户的问题
    with st.chat_message("user"):
        st.markdown(prompt)
    # 把用户问题存入历史
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. AI 开始思考 (显示加载动画)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            with st.status("⏱️ 正在全网检索最新情报...", expanded=True) as status:
                now = datetime.datetime.now()
                current_date_str = now.strftime("%Y年%m月")
                search_query = f"{prompt} {current_date_str} 最新趋势 爆款"
                
                # 搜索
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=6)
                evidence = search.invoke(search_query)
                status.write(f"✅ 采集到 {len(evidence)} 条情报")
                
                # 推理
                status.write("正在撰写报告...")
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.5)
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "老板的需求: {input}\n\n市场情报: {evidence}")
                ]) | llm | StrOutputParser()
                
                full_response = chain.invoke({
                    "input": prompt, 
                    "evidence": evidence,
                    "current_date": now.strftime("%Y-%m-%d")
                })
                
                status.update(label="✅ 完成", state="complete", expanded=False)
            
            # 显示 AI 回复
            message_placeholder.markdown(full_response)
            
            # 4. 把 AI 回复存入历史
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # --- 5. 新增：下载按钮 ---
            # 生成一个独立的文件名，比如 "餐饮报告_20231001.md"
            file_name = f"餐饮情报_{now.strftime('%H%M%S')}.md"
            st.download_button(
                label="💾 下载这份报告",
                data=full_response,
                file_name=file_name,
                mime="text/markdown"
            )

        except Exception as e:
            st.error(f"出错啦: {e}")
