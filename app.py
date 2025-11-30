import streamlit as st
import datetime
import re
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tavily import TavilyClient

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Chef Fusion Gallery (Fixed)",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 样式 ---
st.markdown("""
<style>
    h1 {color: #1A1A1A; font-family: 'Helvetica Neue', sans-serif;}
    .block-container {padding-bottom: 100px;}
    
    .report-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        border-left: 6px solid #C5A059;
        margin-top: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    
    .dish-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        line-height: 1.4;
    }
    
    h4 {
        color: #C5A059 !important;
        font-size: 1.05rem !important;
        font-weight: bold !important;
        margin-top: 20px !important;
        margin-bottom: 8px !important;
        text-transform: uppercase;
    }
    
    p, li {
        font-size: 1rem;
        line-height: 1.6;
        color: #333;
        margin-bottom: 10px;
    }
    
    .plating-box {
        background-color: #F8F8F8;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #333;
        margin-top: 10px;
        color: #555;
        font-size: 0.95rem;
    }
    
    .history-item {
        padding: 8px 10px;
        background: #f0f2f6;
        border-radius: 5px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #555;
        border-left: 3px solid #C5A059;
    }

    /* 图片容器样式 */
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
    }
    .dish-image {
        width: 100%;
        height: 250px;
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

# --- 4. Tavily 搜图 ---
def search_tavily_image(query, api_key):
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="basic", include_images=True, max_results=1)
        if 'images' in response and len(response['images']) > 0:
            return response['images'][0]
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("📜 历史提问")
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
st.title("👨‍🍳 行政总厨 (图文修复版)")
st.caption("v19.1: 修复代码外露问题 • 自动配图 • 研发必备")

# --- 7. Prompt ---
base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"

FUSION_PROMPT_TEXT = """
你是一名精通**【中西融合菜】**的行政总厨。
用户需求："{user_input}"
市场情报："{evidence}"

请提供 **3个** 高溢价的研发方案。

⚠️ **格式铁律：**
1.  **纯 HTML 输出：** 不要用 ```html 包裹。
2.  **不要缩进：** 所有 HTML 标签顶格写。
3.  **不要加链接/图片标签：** 这一步只输出文本结构。
4.  **关键标记：** 在菜名的 `<div>` 里加上 `data-dish-name="菜名"`。

输出模板（HTML）：
<div class="report-card" data-dish-name="菜名1">
<div class="dish-title">1. 菜名1</div>
<h4>💡 中西融合灵感</h4>
<p>解释融合点...</p>
<h4>👨‍🍳 核心食材与技法</h4>
<p>列出关键材料...</p>
<h4>🎨 摆盘美学 (Plating)</h4>
<div class="plating-box">
<p><strong>器皿：</strong>...</p>
<p><strong>构图：</strong>...</p>
</div>
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

user_input = st.chat_input("输入研发需求（例如：做一道有仪式感的牛肉菜）...")

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
            with st.spinner("👨‍🍳 总厨正在构思方案..."):
                search_query = f"{user_input} 高端摆盘 中西融合菜 做法 创意 plating"
                search = TavilySearchResults(tavily_api_key=tavily_key, max_results=5)
                evidence = search.invoke(search_query)
                
                llm = ChatOpenAI(base_url=base_url, api_key=deepseek_key, model=model_name, temperature=0.7)
                chain = ChatPromptTemplate.from_messages([
                    ("system", FUSION_PROMPT_TEXT),
                    ("user", "") 
                ]) | llm | StrOutputParser()
                
                text_response = chain.invoke({"user_input": user_input, "evidence": evidence})
                
                # 清洗代码
                text_response = re.sub(r"```[a-zA-Z]*", "", text_response).replace("```", "")
                cleaned_lines = [line.strip() for line in text_response.split('\n')]
                text_response = "\n".join(cleaned_lines)

            # --- 自动配图 (修复版) ---
            final_response = text_response
            dish_names = re.findall(r'data-dish-name="([^"]+)"', text_response)
            
            with st.status("🖼️ 正在搜寻配图...", expanded=True) as status:
                for i, dish_name in enumerate(dish_names):
                    status.write(f"正在找图：{dish_name}")
                    img_query = f"{dish_name} 精致菜品摄影 实拍图"
                    image_url = search_tavily_image(img_query, tavily_key)
                    
                    if image_url:
                        # 🔥 核心修复：这里把 HTML 写成死死的一行，绝对不换行，不缩进！
                        # 这样 Streamlit 就不会把它误判成代码块了
                        image_html = f'<div class="dish-image-container"><img src="{image_url}" class="dish-image" alt="{dish_name}" onerror="this.style.display=\'none\'"><div class="image-caption">参考图源：Tavily AI Search</div></div>'
                        
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
                label="📥 下载图文报告",
                data=final_response,
                file_name=f"研发方案_{now_str}.html",
                mime="text/html"
            )

        except Exception as e:
            st.error(f"运行出错: {e}")
