import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 ---
st.set_page_config(page_title="FoodHunter - 餐饮情报官", page_icon="🦞", layout="wide")
st.title("🦞 FoodHunter: AI 餐饮研发总监 (自动登录版)")

# --- 2. 自动获取密钥 (核心修改) ---
# 逻辑：先去保险箱(Secrets)找，找不到再让用户输
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return None

# 尝试从后台获取 Key
deepseek_key = get_api_key("DEEPSEEK_API_KEY")
tavily_key = get_api_key("TAVILY_API_KEY")

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.header("🔑 系统配置")
    
    # 如果后台没配 Key，才显示输入框
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek API Key", type="password")
    else:
        st.success("✅ DeepSeek Key 已自动加载")

    if not tavily_key:
        tavily_key = st.text_input("Tavily API Key", type="password")
    else:
        st.success("✅ Tavily Key 已自动加载")
        
    # 固定模型配置
    base_url = "https://api.deepseek.com"
    model_name = "deepseek-chat" 

# --- 4. 核心 Prompt ---
TREND_HUNTER_PROMPT = """
你是一名拥有15年经验的【餐饮研发总监】兼【品牌营销专家】。
你熟悉中国餐饮市场，擅长通过网络数据挖掘最新的【爆款菜品】、【流行口味】和【营销玩法】。

你的任务是基于【搜索结果】，回答老板的调研需求。

请严格按照以下结构输出策划案：

# 💡 餐饮情报分析报告

### 1. 🎯 核心趋势提炼
(用一句话总结目前的市场热点)

### 2. 🍲 爆款拆解 (What & Why)
* **流行产品/口味：**
* **火爆逻辑：**
* **典型案例：**

### 3. 🛠️ 落地建议 (Action Plan)
* **如果不换菜单：** (现有食材微调建议)
* **如果推新品：** (新菜名+做法)
* **营销话术：** (朋友圈/抖音文案)

---
**数据来源：** {evidence}
"""

# --- 5. 主逻辑 ---
user_input = st.text_area("你想了解什么？", height=100, 
                         placeholder="例如：\n1. 最近火锅店有什么新的甜品爆款？\n2. 现在的年轻人喜欢吃什么口味的烤鱼？")

check_btn = st.button("🔍 开始挖掘灵感", type="primary")

if check_btn:
    if not deepseek_key or not tavily_key:
        st.error("❌ 缺少 API Key，请在侧边栏输入或在 Secrets 中配置")
    else:
        try:
            with st.status("👨‍🍳 正在全网搜罗美食情报...", expanded=True) as status:
                
                # 1. 搜索
                status.write("正在检索流行趋势 (via Tavily)...")
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                query = f"{user_input} 最新餐饮趋势 爆款"
                evidence = search.invoke(query)
                status.write(f"✅ 采集到 {len(evidence)} 条市场情报")
                
                # 2. 推理
                status.write("研发总监 (DeepSeek) 正在撰写策划案...")
                llm = ChatOpenAI(
                    base_url=base_url,
                    api_key=deepseek_key,
                    model=model_name,
                    temperature=0.7
                )
                
                chain = ChatPromptTemplate.from_messages([
                    ("system", TREND_HUNTER_PROMPT),
                    ("user", "老板的需求: {input}\n\n市场情报: {evidence}")
                ]) | llm | StrOutputParser()
                
                report = chain.invoke({"input": user_input, "evidence": evidence})
                status.update(label="✅ 策划案已生成", state="complete", expanded=False)
            
            st.markdown(report)
            
        except Exception as e:
            st.error(f"出错啦: {e}")
