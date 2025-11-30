import streamlit as st
import datetime
import re
import requests
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tavily import TavilyClient

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef R&D Pro",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 样式 (增加了步骤列表的样式) ---
st.markdown("""
<style>
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    .block-container {padding-bottom: 100px;}
    
    .report-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        border-left: 6px solid #B71C1C; /* 改回深红色，代表中式高端 */
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

    /* 图片容器 */
    .dish-image-container {
        margin-top: 15px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        background: #f9f9f9;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        border: 1px solid #eee;
    }
    .dish-image {
        width: 100%;
        height: 280px;
        object-fit: cover;
        display: block;
    }
    .image-caption {
        font-size: 0.8rem;
        color: #888;
        padding: 8px;
        font-style: italic;
        width: 100%;
        text-align: center;
        background: #fafafa;
        border-top: 1px solid #eee;
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

# --- 4. 辅助函数：搜图 + 验图 ---
def search_tavily_image(query, api_key):
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="basic", include_images=True, max_results=1)
        if 'images' in response and len(response['images']) > 0:
            return response['images'][0]
        return None
    except Exception as e:
        return None

def check_image_validity(url):
    if not url: return False
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.head(url, headers=headers, timeout=1.5)
        if r.status_code in [405, 403]:
             r = requests.get(url, headers=headers, stream=True, timeout=1.5)
        if r.status_code == 200:
            return True
    except:
        return False
    return False

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
st.title("👨‍🍳 研发总监 (深度SOP版)")
st.caption("v21.0: 中式创意 • 包含具体食材与烹饪步骤 • 严查图片")

# --- 7. Prompt (核心升级：增加SOP和中式比重) ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

RD_PROMPT_TEXT = """
你是一名拥有25年经验的**【中餐研发总监】**，精通潮汕菜、粤菜，并熟悉分子料理和西餐摆盘。
你的设计风格是：**"中魂西技"**（Chinese Soul, Modern Presentation）。

用户需求："{user_input}"
市场情报："{evidence}"

请设计 **3道** 高溢价的创意菜品，方向如下：
1.  **【新中式·意境菜】**：保留传统口味，但在形态和器皿上极具东方美学（如山水意境）。
2.  **【中西·高定融合】**：用西式顶级食材（如黑松露、鱼子酱）赋能中式经典菜。
3.  **【功夫·位上菜】**：体现繁复手工和火候，适合按位上的高端菜。

⚠️ **格式铁律：**
1.  **纯 HTML 输出**，顶格写，不要缩进，不要 ```html。
2.  **内容详实：** 必须包含具体的【食材清单】和【SOP步骤】。
3.  **不加链接**。

输出模板（HTML）：
<div class="report-card" data-dish-name="菜名1">
<div class="dish-title">1. 菜名1</div>
<p><strong>💡 研发理念：</strong>(一句话讲出卖点，如"用西式慢煮重塑潮汕卤水")</p>

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

<div class="image-placeholder"></div>
</div>

(请重复3次，分别对应三个方案)
"""

# --- 8. 主程序 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.markdown(msg["content"], unsafe_allow_html=True)
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
                # 搜索策略：增加 "做法" "食谱" "配方" 等关键词
                search_query = f"{user_input} 高端中餐 创意菜 做法食谱 详细配方plating"
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.6) # 温度调低，让步骤更严谨
                chain = ChatPromptTemplate.from_messages([
                    ("system", RD_PROMPT_TEXT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                text_response = chain.invoke({"user_input": user_input, "evidence": evidence})
                
                # 清洗代码
                text_response = re.sub(r"```[a-zA-Z]*", "", text_response).replace("```", "")
                cleaned_lines = [line.strip() for line in text_response.split('\n')]
                text_response = "\n".join(cleaned_lines)

            # --- 自动配图 (严查版) ---
            final_response = text_response
            dish_names = re.findall(r'data-dish-name="([^"]+)"', text_response)
            
            with st.status("🖼️ 正在搜寻参考图...", expanded=True) as status:
                for i, dish_name in enumerate(dish_names):
                    status.write(f"正在找图：{dish_name}")
                    img_query = f"{dish_name} 精致中餐摆盘 实拍图"
                    image_url = search_tavily_image(img_query, tavily_key)
                    
                    is_valid = False
                    if image_url:
                        if check_image_validity(image_url):
                            is_valid = True
                    
                    if is_valid:
                        image_html = f"""<div class="dish-image-container"><img src="{image_url}" class="dish-image" alt="{dish_name}"><div class="image-caption">参考图源：Tavily AI Search</div></div>"""
                        final_response = final_response.replace('<div class="image-placeholder"></div>', image_html, 1)
                    else:
                        final_response = final_response.replace('<div class="image-placeholder"></div>', '', 1)
                        
                status.update(label="✅ 完成", state="complete", expanded=False)

            # 显示最终结果
            placeholder.markdown(final_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            # 下载按钮
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
            st.download_button(
                label="📥 下载SOP研发方案",
                data=final_response,
                file_name=f"研发SOP_{now_str}.html",
                mime="text/html"
            )

        except Exception as e:
            st.error(f"运行出错: {e}")
