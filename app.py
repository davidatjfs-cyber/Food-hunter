import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. 页面配置 (换成美食主题) ---
st.set_page_config(page_title="FoodHunter - 餐饮情报官", page_icon="🦞", layout="wide")

st.title("🦞 FoodHunter: 您的 AI 餐饮研发总监")
st.markdown("### 专查：爆款菜品 / 流行口味 / 营销灵感 / 竞品分析")

# --- 2. 侧边栏 (保持不变，方便你直接用) ---
with st.sidebar:
    st.header("🔑 系统配置")
    
    # 默认选 DeepSeek，因为你已经充值了
    provider = st.selectbox("选择模型厂商", ["DeepSeek (深度求索)", "OpenAI", "Moonshot (Kimi)"])
    
    if provider == "OpenAI":
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4o"
    elif provider == "DeepSeek (深度求索)":
        base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat" 
    elif provider == "Moonshot (Kimi)":
        base_url = "https://api.moonshot.cn/v1"
        model_name = "moonshot-v1-8k"

    # 这里提醒用户填 Key
    llm_api_key = st.text_input("大模型 API Key", type="password", help="推荐使用 DeepSeek")
    tavily_api_key = st.text_input("Tavily API Key", type="password", help="搜索专用")

# --- 3. 核心 Prompt (这是本次改造的灵魂！) ---
# 我们把“审计师”换成了“餐饮研发总监”
TREND_HUNTER_PROMPT = """
你是一名拥有15年经验的【餐饮研发总监】兼【品牌营销专家】。
你熟悉中国餐饮市场，擅长通过网络数据挖掘最新的【爆款菜品】、【流行口味】和【营销玩法】。

你的任务是基于【搜索结果】，回答老板的调研需求。

请严格按照以下结构输出策划案：

# 💡 餐饮情报分析报告

### 1. 🎯 核心趋势提炼
(用一句话总结目前的市场热点，例如："脆皮五花肉正在夜市和抖音爆火，核心在于听觉刺激")

### 2. 🍲 爆款拆解 (What & Why)
* **流行产品/口味：** (具体是什么菜？什么搭配？例如：火锅+奶茶)
* **火爆逻辑：** (为什么年轻人喜欢？是拍照好看？性价比高？还是口味猎奇？)
* **典型案例：** (搜索结果中提到的做得好的品牌或店铺)

### 3. 🛠️ 落地建议 (Action Plan)
* **如果不换菜单：** (如何用现有食材微调来蹭热点？)
* **如果推新品：** (给出一个具体的新菜名和简单的做法/摆盘建议)
* **营销话术：** (写一句发朋友圈/抖音的文案，要吸引人)

---
**数据来源：** {evidence}
"""

# --- 4. 主逻辑 ---
# 修改了示例问题
user_input = st.text_area("你想了解什么？", height=100, 
                         placeholder="例如：\n1. 最近火锅店有什么新的甜品爆款？\n2. 现在的年轻人喜欢吃什么口味的烤鱼？\n3. 帮我查查‘加上头’这家店为什么火？")

check_btn = st.button("🔍 开始挖掘灵感", type="primary")

if check_btn:
    if not llm_api_key or not tavily_api_key:
        st.error("❌ 别忘了在左侧填入 API Keys (DeepSeek 和 Tavily)")
    else:
        try:
            with st.status("👨‍🍳 正在全网搜罗美食情报...", expanded=True) as status:
                
                # 1. 搜索
                status.write("正在检索小红书/大众点评/抖音的流行趋势 (via Tavily)...")
                search = TavilySearchResults(tavily_api_key=tavily_api_key, max_results=5)
                # 自动在搜索词后加上“趋势”、“爆款”等词，提高搜索质量
                query = f"{user_input} 最新餐饮趋势 爆款"
                evidence = search.invoke(query)
                status.write(f"✅ 采集到 {len(evidence)} 条市场情报")
                
                # 2. 推理
                status.write(f"研发总监 ({provider}) 正在撰写策划案...")
                llm = ChatOpenAI(
                    base_url=base_url,
                    api_key=llm_api_key,
                    model=model_name,
                    temperature=0.7 # 稍微调高一点，让 AI 更有创意
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
