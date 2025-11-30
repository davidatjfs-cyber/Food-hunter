import streamlit as st
import datetime # 引入时间模块
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(page_title="FoodHunter - 餐饮情报官", page_icon="🦞", layout="wide")
st.title("🦞 FoodHunter: 强时效版 (只看最新趋势)")

# --- 2. 自动获取密钥 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header("🔑 系统配置")
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek API Key", type="password")
    else:
        st.success("✅ DeepSeek Key 已自动加载")

    if not tavily_key:
        tavily_key = st.text_input("Tavily API Key", type="password")
    else:
        st.success("✅ Tavily Key 已自动加载")
        
    base_url = "https://api.deepseek.com"
    model_name = "deepseek-chat" 

# --- 4. 核心 Prompt (加入时间过滤机制) ---
TREND_HUNTER_PROMPT = """
你是一名拥有15年经验的【餐饮研发总监】。
今天是：{current_date}。

你的核心原则是：**【只关注最新趋势】**。
请根据搜索结果回答老板的问题。

⚠️ **严格的时间审查机制：**
1. 优先采用 **近3个月内** 的数据和案例。
2. 如果搜索结果是 **1年前** 的旧闻（除非是经典案例），请直接忽略或明确标注“这是去年的数据”。
3. 如果搜索结果没有明确时间，请根据内容上下文判断是否过时。

请输出策划案：
# 💡 餐饮情报分析报告 (日期: {current_date})

### 1. 🎯 本月/本季核心趋势
(一句话总结当下的热点)

### 2. 🍲 最新爆款拆解
* **流行产品：**
* **火爆逻辑：**
* **参考案例：** (必须注明是哪家店，最近什么时候火的)

### 3. 🛠️ 落地建议
* **新品建议：**
* **营销文案：**

---
**数据来源与时间戳：** {evidence}
"""

# --- 5. 主逻辑 ---
user_input = st.text_area("你想了解什么最新情报？", height=100, 
                         placeholder="例如：最近上海夜市最火的小吃是什么？")

check_btn = st.button("🔍 挖掘最新情报", type="primary")

if check_btn:
    if not deepseek_key or not tavily_key:
        st.error("❌ 缺少 API Key")
    else:
        try:
            with st.status("⏱️ 正在锁定最新时间线...", expanded=True) as status:
                
                # 1. 获取当前时间 (比如: 2024年5月)
                now = datetime.datetime.now()
                current_date_str = now.strftime("%Y年%m月")
                
                # 2. 构造带时间的搜索词 (强制搜索最新)
                # 技巧：加上 "after:2024-01-01" 这种语法有助于部分引擎，但直接加年份月份最稳妥
                search_query = f"{user_input} {current_date_str} 最新趋势 爆款"
                
                status.write(f"正在全网检索关键词: 「{search_query}」...")
                
                # Tavily 搜索
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=6)
                evidence = search.invoke(search_query)
                status.write(f"✅ 采集到 {len(evidence)} 条情报")
                
                # 3. 推理
                status.write("正在过滤旧闻，提炼新趋势...")
                llm = ChatOpenAI(
                    base_url=base_url,
                    api_key=deepseek_key,
                    model=model_name,
                    temperature=0.5 # 调低一点，让它更严谨
                )
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "老板的需求: {input}\n\n市场情报: {evidence}")
                ]) | llm | StrOutputParser()
                
                # 把当前日期传给 AI
                report = chain.invoke({
                    "input": user_input, 
                    "evidence": evidence,
                    "current_date": now.strftime("%Y-%m-%d") 
                })
                status.update(label="✅ 最新报告已生成", state="complete", expanded=False)
            
            st.markdown(report)
            
        except Exception as e:
            st.error(f"出错啦: {e}")
