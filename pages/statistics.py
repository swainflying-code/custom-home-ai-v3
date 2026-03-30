"""
成交魔方 V3 - 数据统计 & 老板周报
"""
import logging
import streamlit as st
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def show_statistics_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">📊 数据统计</h2>
        <p style="margin:4px 0 0 0; color:#666;">门店经营数据一览，一键生成老板周报</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📈 数据看板", "📋 老板周报"])

    # ── 数据看板 ──────────────────────────────────────────────────
    with tab1:
        col1, col2, col3, col4 = st.columns(4)

        try:
            from core.database import db
            total = db.count("customers")
            high = db.count("customers", {"intent_level": "高意向（1个月内）"})
            medium = db.count("customers", {"intent_level": "中意向（3个月内）"})
            low = db.count("customers", {"intent_level": "低意向（3个月以上）"})
        except Exception as e:
            total, high, medium, low = 0, 0, 0, 0
            st.warning(f"数据加载失败：{str(e)[:60]}")

        with col1:
            st.metric("总客户数", total)
        with col2:
            st.metric("🟢 高意向", high, delta=None)
        with col3:
            st.metric("🟡 中意向", medium)
        with col4:
            st.metric("🔴 低意向", low)

        st.markdown("---")

        # 最近客户列表
        st.markdown("#### 最近录入的客户")
        try:
            from core.database import db
            recent = db.select("customers", order_by="created_at.desc", limit=20)
            if recent:
                import pandas as pd
                df = pd.DataFrame(recent)
                display_cols = [c for c in [
                    "customer_no", "customer_name", "contact",
                    "budget_range", "intent_level", "next_step", "created_at"
                ] if c in df.columns]
                col_rename = {
                    "customer_no": "编号", "customer_name": "姓名", "contact": "联系方式",
                    "budget_range": "预算", "intent_level": "意向", "next_step": "下一步", "created_at": "录入时间"
                }
                st.dataframe(
                    df[display_cols].rename(columns=col_rename),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("暂无客户数据")
        except Exception as e:
            st.warning(f"客户列表加载失败：{str(e)[:80]}")

    # ── 老板周报 ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📋 老板周报生成器")
        st.caption("每周一自动汇总，也可手动填写数据生成")

        with st.form("weekly_report_form"):
            st.markdown("**📥 填写本周数据**（无数据可留0）")
            col_a, col_b = st.columns(2)
            with col_a:
                total_visits = st.number_input("进店客户总数（门店手工计数）", min_value=0, value=0, step=1)
                total_system = st.number_input("系统记录客户数（本系统填写数）", min_value=0, value=0, step=1)
                total_deals = st.number_input("本周成交数", min_value=0, value=0, step=1)
                high_intent_count = st.number_input("高意向客户数", min_value=0, value=0, step=1)
                followed_count = st.number_input("高意向中已跟进数", min_value=0, value=0, step=1)
            with col_b:
                overdue_count = st.number_input("超3天未跟进客户数", min_value=0, value=0, step=1)
                avg_order_value = st.number_input("平均客单价（万元）", min_value=0.0, value=5.0, step=0.5)
                last_week_visits = st.number_input("上周进店数（环比用）", min_value=0, value=0, step=1)
                last_week_deals = st.number_input("上周成交数（环比用）", min_value=0, value=0, step=1)
                urgent_customers_input = st.text_input(
                    "⚠️ 即将流失客户（逗号分隔）",
                    placeholder="如：张女士5天、李先生4天"
                )

            generate_btn = st.form_submit_button("🤖 一键生成老板周报", type="primary", use_container_width=True)

        if generate_btn:
            # 计算统计数据
            deal_rate = round(total_deals / total_visits * 100, 1) if total_visits > 0 else 0
            usage_rate = round(total_system / total_visits * 100, 1) if total_visits > 0 else 0
            not_followed = high_intent_count - followed_count
            potential_loss = round(overdue_count * avg_order_value, 1)

            def _change_str(curr, prev):
                if prev == 0:
                    return "（无上周数据）"
                diff = curr - prev
                pct = round(abs(diff) / prev * 100, 1)
                arrow = "↑" if diff >= 0 else "↓"
                return f"{arrow}{pct}%"

            weekly_stats = {
                "进店客户总数": total_visits,
                "系统记录客户数": total_system,
                "系统使用率": f"{usage_rate}%",
                "本周成交数": total_deals,
                "成交率": f"{deal_rate}%",
                "高意向客户数": high_intent_count,
                "高意向中已跟进": followed_count,
                "高意向中未跟进": not_followed,
                "超3天未跟进客户数": overdue_count,
                "平均客单价(万元)": avg_order_value,
                "潜在损失估算(万元)": potential_loss,
                "上周进店数": last_week_visits,
                "上周成交数": last_week_deals,
                "进店环比": _change_str(total_visits, last_week_visits),
                "成交环比": _change_str(total_deals, last_week_deals),
                "即将流失客户": urgent_customers_input or "暂无",
            }

            with st.spinner("🤖 正在生成老板周报..."):
                try:
                    from core.ai_service import get_ai_service
                    ai = get_ai_service()
                    report = ai.generate_weekly_report(weekly_stats)
                    st.markdown("---")
                    st.markdown("#### 📋 本周老板周报")
                    st.markdown(f"""
                    <div style="background:#f8fff8; border:1px solid #90EE90; border-radius:8px; padding:20px; white-space:pre-wrap; font-size:15px; line-height:2;">
{report}
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"生成时间：{date.today().strftime('%Y年%m月%d日')} | 数据范围：本周")
                except Exception as e:
                    st.error(f"❌ 周报生成失败：{str(e)}")
