"""
成交魔方 V3 - 预算锚定引擎（占位）
提供可解释的预算区间、方案分级和价格影响因素，减少无效报价和预算错配
"""
import streamlit as st


def show_budget_anchor_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">💰 预算锚定引擎</h2>
        <p style="margin:4px 0 0 0; color:#666;">提供可解释的预算区间、方案分级和价格影响因素，减少无效报价和预算错配</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("🚧 预算锚定引擎开发中，敬请期待")

    st.markdown("""
    **即将上线功能：**
    - 💡 预算区间自动匹配（基于空间+材质）
    - 📊 方案分级对比（基础款/标准款/高端款）
    - 🔍 价格影响因子解释
    - 📋 报价单模板生成
    - 🤝 让客户"听懂"为什么这个价格值
    """)
