"""
成交魔方 V3 - 主应用入口
让每一个客户，都走到成交
"""

import os
import sys
import traceback

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from streamlit_option_menu import option_menu

# ============================================================
# 页面配置（必须是第一个 st 调用）
# ============================================================
st.set_page_config(
    page_title="成交魔方 · 让每一个客户，都走到成交",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 全局 CSS
# ============================================================
st.markdown("""
<style>
/* ─── 品牌色变量 ─── */
:root {
    --brand-gold: #c9a84c;
    --brand-dark: #1a1a2e;
    --brand-bg: #f7f8fc;
    --sidebar-bg: #1a1a2e;
}

/* ─── 侧边栏品牌区 ─── */
.sidebar-brand {
    text-align: center;
    padding: 20px 12px 12px;
}
.sidebar-brand .brand-icon {
    font-size: 40px;
    line-height: 1;
}
.sidebar-brand .brand-name {
    font-size: 22px;
    font-weight: 800;
    color: #c9a84c;
    letter-spacing: 3px;
    margin: 8px 0 2px;
}
.sidebar-brand .brand-tagline {
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    letter-spacing: 1px;
}

/* ─── 登录页 ─── */
.login-wrap {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
.login-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(201,168,76,0.3);
    border-radius: 20px;
    padding: 48px 40px;
    text-align: center;
    backdrop-filter: blur(20px);
}
.login-icon { font-size: 56px; }
.login-title {
    font-size: 32px;
    font-weight: 800;
    color: #c9a84c;
    letter-spacing: 4px;
    margin: 12px 0 4px;
}
.login-tagline {
    font-size: 13px;
    color: rgba(255,255,255,0.55);
    letter-spacing: 2px;
    margin-bottom: 32px;
}

/* ─── 通用卡片 ─── */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border-left: 4px solid #c9a84c;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State 初始化
# ============================================================
def init_session():
    defaults = {
        'logged_in': False,
        'user_info': None,
        'current_page': '客户诊断',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ============================================================
# 登录页
# ============================================================
def show_login():
    # 深色背景覆盖
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; padding: 60px 0 32px;">
            <div style="font-size:60px;">🎯</div>
            <div style="font-size:36px; font-weight:900; color:#c9a84c; letter-spacing:5px; margin:12px 0 6px;">成交魔方</div>
            <div style="font-size:13px; color:rgba(255,255,255,0.5); letter-spacing:2px; margin-bottom:40px;">让每一个客户，都走到成交</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            btn = st.form_submit_button("🚀 进入系统", type="primary", use_container_width=True)

            if btn:
                if not username.strip() or not password.strip():
                    st.error("请填写用户名和密码")
                else:
                    # 尝试数据库认证
                    authed = False
                    try:
                        from core.database import db
                        from core.auth import AuthManager
                        result = db.client.table("users").select("*").eq("username", username).execute()
                        if result.data:
                            auth = AuthManager()
                            ok, info = auth.authenticate(username, password, result.data[0])
                            if ok:
                                st.session_state.logged_in = True
                                st.session_state.user_info = info
                                authed = True
                    except Exception:
                        pass

                    # 默认账户兜底
                    if not authed:
                        default_accounts = {"admin": "admin123", "user": "user123"}
                        if default_accounts.get(username) == password:
                            st.session_state.logged_in = True
                            st.session_state.user_info = {
                                "username": username,
                                "role": "admin" if username == "admin" else "user",
                                "display_name": "系统管理员" if username == "admin" else "销售员"
                            }
                            authed = True

                    if authed:
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误")

        st.markdown("""
        <div style="text-align:center; color:rgba(255,255,255,0.25); font-size:11px; margin-top:24px;">
            默认账号：admin / admin123
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# 主应用
# ============================================================
def show_main():
    selected_page = st.session_state.get('current_page', '客户诊断')

    try:
        with st.sidebar:
            # 品牌区
            st.markdown("""
            <div class="sidebar-brand">
                <div class="brand-icon">🎯</div>
                <div class="brand-name">成交魔方</div>
                <div class="brand-tagline">让每一个客户，都走到成交</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")

            # 导航菜单
            pages = ["客户诊断", "方案引导", "预算锚定", "成交推进", "数据统计", "系统设置"]
            icons = ["clipboard2-pulse", "palette2", "cash-coin", "rocket-takeoff", "graph-up-arrow", "gear"]
            current_idx = pages.index(selected_page) if selected_page in pages else 0

            selected_page = option_menu(
                menu_title=None,
                options=pages,
                icons=icons,
                default_index=current_idx,
                styles={
                    "container": {"padding": "0", "background-color": "transparent"},
                    "icon": {"color": "#c9a84c", "font-size": "16px"},
                    "nav-link": {
                        "font-size": "13px",
                        "text-align": "left",
                        "margin": "2px 0",
                        "padding": "10px 14px",
                        "border-radius": "8px",
                        "color": "#333",
                    },
                    "nav-link-selected": {
                        "background-color": "#c9a84c",
                        "color": "#1a1a1a",
                        "font-weight": "700",
                    },
                },
            )
            st.session_state.current_page = selected_page
            st.markdown("---")

            # 用户信息
            user = st.session_state.get('user_info') or {}
            st.markdown(f"""
            <div style="padding:8px 4px; font-size:12px; color:#666;">
                👤 <strong>{user.get('display_name', user.get('username', '未知'))}</strong>
                &nbsp;·&nbsp; {user.get('role', '销售员')}
            </div>
            """, unsafe_allow_html=True)

            # 快速数据
            try:
                from core.database import db
                total = db.count("customers_v3")
                high = db.count("customers_v3", {"intent_level": "高"})
                st.metric("📋 总客户", total)
                st.metric("🟢 高意向", high)
            except Exception:
                pass

            st.markdown("---")
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_info = None
                st.rerun()

    except Exception as e:
        st.error(f"侧边栏加载失败：{e}")

    # 路由到各引擎
    try:
        if selected_page == "客户诊断":
            from pages.customer_diagnosis import show_customer_diagnosis_page
            show_customer_diagnosis_page()

        elif selected_page == "方案引导":
            from pages.solution_guide import show_solution_guide_page
            show_solution_guide_page()

        elif selected_page == "预算锚定":
            from pages.budget_anchor import show_budget_anchor_page
            show_budget_anchor_page()

        elif selected_page == "成交推进":
            from pages.deal_push import show_deal_push_page
            show_deal_push_page()

        elif selected_page == "数据统计":
            from pages.statistics import show_statistics_page
            show_statistics_page()

        elif selected_page == "系统设置":
            _show_settings()

        else:
            st.warning(f"页面 '{selected_page}' 尚未实现")

    except Exception as e:
        st.error(f"页面加载失败：{str(e)}")
        with st.expander("错误详情"):
            st.code(traceback.format_exc())


def _show_settings():
    st.markdown("### ⚙️ 系统设置")
    st.info("系统设置功能开发中")
    st.markdown("""
    **版本信息**
    - 应用：成交魔方 V3.0
    - 广告语：让每一个客户，都走到成交
    - 四大引擎：客户诊断 / 方案引导 / 预算锚定 / 成交推进
    """)


# ============================================================
# 主流程入口
# ============================================================
try:
    from core.config import config
    if not config.is_valid():
        missing = config.get_missing_configs()
        st.error("⚠️ 配置不完整，请在 Streamlit Cloud Secrets 中添加以下配置：")
        for item in missing:
            st.markdown(f"- `{item}`")
        with st.expander("配置示例"):
            st.code("""
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "your-anon-key"
SUPABASE_JWT_SECRET = "your-jwt-secret"
MIMO_API_KEY = "your-mimo-key"
MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
MIMO_MODEL = "mimo-v2-pro"
SECRET_KEY = "your-secret-key"
""", language="toml")
        st.stop()

    if not st.session_state.logged_in:
        show_login()
    else:
        show_main()

except SystemExit:
    raise
except Exception as e:
    st.error(f"应用启动失败：{str(e)}")
    with st.expander("错误详情"):
        st.code(traceback.format_exc())
