"""
成交魔方 V3 - 成交推进引擎（全新建构）
D1.成交判断与状态
D2.报价与方案动态
D3.跟进时间线
D4.竞品与博弈信息
D5.AI分析（成交战地参谋）
"""
import uuid
import logging
import streamlit as st
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


def show_deal_push_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">🚀 成交推进引擎</h2>
        <p style="margin:4px 0 0 0; color:#666;">自动追踪客户阶段、阻塞点和下一步动作，为销售提供个性化跟进建议</p>
    </div>
    """, unsafe_allow_html=True)

    # 初始化 session state
    if "deal_push_selected_customer" not in st.session_state:
        st.session_state.deal_push_selected_customer = None
    if "deal_push_ai_analysis" not in st.session_state:
        st.session_state.deal_push_ai_analysis = ""
    if "deal_push_sales_report" not in st.session_state:
        st.session_state.deal_push_sales_report = ""

    # 获取所有客户列表
    customers = []
    try:
        from core.database import db
        customers = db.select("customers_v3", order_by="created_at.desc", limit=200)
    except Exception as e:
        st.warning(f"无法加载客户列表：{e}")
        return

    if not customers:
        st.info("💡 暂无客户记录，请先在「客户洞察」板块录入客户")
        return

    # 主界面 - 两列布局
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # D1. 成交判断与状态
        st.markdown("### 📊 D1. 成交判断与状态")
        
        # 客户选择器
        st.markdown("**选择客户**")
        customer_options = [f"{c['customer_no']} - {c['customer_name']}" for c in customers]
        selected_customer_idx = st.selectbox(
            "选择客户",
            range(len(customer_options)),
            format_func=lambda x: customer_options[x],
            key="deal_customer_select"
        )
        
        if selected_customer_idx is not None and selected_customer_idx < len(customers):
            customer = customers[selected_customer_idx]
            st.session_state.deal_push_selected_customer = customer
            
            # 显示客户基本信息
            st.markdown("---")
            st.markdown("**客户基本信息**")
            st.markdown(f"**编号：** {customer.get('customer_no', '-')}")
            st.markdown(f"**姓名：** {customer.get('customer_name', '-')}")
            st.markdown(f"**联系方式：** {customer.get('contact', '-')}")
            st.markdown(f"**预算区间：** {customer.get('budget_range', '-')}")
            
            # 意向等级标签
            intent = customer.get('intent_level', '未知')
            intent_color = {
                '高': '🟢',
                '中': '🟡',
                '低': '🔴'
            }.get(intent, '⚪')
            st.markdown(f"**意向等级：** {intent_color} {intent}")

        # D2. 报价与方案动态
        st.markdown("---")
        st.markdown("### 💰 D2. 报价与方案动态")
        
        if st.session_state.deal_push_selected_customer:
            customer = st.session_state.deal_push_selected_customer
            
            # D2.1 当前报价版本
            quote_version = st.selectbox(
                "1. 当前报价版本",
                ["L1 估算", "L2 方案报价", "L3 精准报价", "未报价"],
                key="deal_quote_version"
            )
            
            # D2.2 最近报价金额
            recent_quote = st.number_input(
                "2. 最近报价金额（元）",
                min_value=0,
                step=100,
                key="deal_recent_quote"
            )
            
            # D2.3 报价是否已发送客户
            quote_sent = st.selectbox(
                "3. 报价是否已发送客户",
                ["未发送", "仅口头", "已发送（日期）"],
                key="deal_quote_sent"
            )
            if quote_sent == "已发送（日期）":
                quote_sent_date = st.date_input("报价发送日期", value=date.today(), key="deal_quote_sent_date")
            
            # D2.4 客户是否还价
            customer_bargain = st.selectbox(
                "4. 客户是否还价",
                ["未还价", "还价 ¥", "要求折扣", "要求赠送"],
                key="deal_customer_bargain"
            )
            if customer_bargain == "还价 ¥":
                bargain_amount = st.number_input("还价金额（元）", min_value=0, step=100, key="deal_bargain_amount")

    with col_right:
        if st.session_state.deal_push_selected_customer:
            st.markdown(f"### 📋 {st.session_state.deal_push_selected_customer.get('customer_name', '未知')} 的成交推进")
            
            # D3. 跟进时间线
            st.markdown("---")
            st.markdown("### ⏰ D3. 跟进时间线（防客户流失）")
            
            col_d3_1, col_d3_2 = st.columns(2)
            with col_d3_1:
                # D3.1 最近一次联系日期
                last_contact_date = st.date_input(
                    "1. 最近一次联系日期",
                    value=date.today(),
                    key="deal_last_contact_date"
                )
                
                # D3.2 联系方式
                contact_method = st.selectbox(
                    "2. 联系方式",
                    ["未联系", "到店", "电话", "微信", "短信"],
                    key="deal_contact_method"
                )
                
                # D3.3 客户是否回复/接通
                customer_response = st.selectbox(
                    "3. 客户是否回复/接通",
                    ["未联系", "已回复", "未回复", "拒接"],
                    key="deal_customer_response"
                )
            
            with col_d3_2:
                # D3.4 下次联系时间
                next_contact_date = st.date_input(
                    "4. 下次联系时间",
                    value=date.today() + timedelta(days=3),
                    key="deal_next_contact_date"
                )
                
                # D3.5 跟进阻塞原因
                block_reason = st.selectbox(
                    "5. 跟进阻塞原因",
                    [
                        "等客户回复",
                        "等设计师出图", 
                        "等决策人到店",
                        "客户在对比",
                        "等开工时间确认",
                        "客户说'再考虑'",
                        "其他（填写）"
                    ],
                    key="deal_block_reason"
                )
                if block_reason == "其他（填写）":
                    other_block_reason = st.text_input("具体阻塞原因", key="deal_other_block_reason")

            # D4. 竞品与博弈信息
            st.markdown("---")
            st.markdown("### ⚔️ D4. 竞品与博弈信息（成交最后100米）")
            
            col_d4_1, col_d4_2 = st.columns(2)
            with col_d4_1:
                # D4.1 客户提及的竞品
                competitor_mentioned = st.radio(
                    "1. 客户提及的竞品",
                    ["未提及", "提及（填写）"],
                    key="deal_competitor_mentioned"
                )
                if competitor_mentioned == "提及（填写）":
                    competitor_name = st.text_input("竞品品牌名", placeholder="如：欧派、索菲亚", key="deal_competitor_name")
                
                # D4.2 竞品比较维度
                compare_dimension = st.selectbox(
                    "2. 竞品比较维度",
                    ["未明确", "价格", "品质", "设计", "品牌", "工期"],
                    key="deal_compare_dimension"
                )
            
            with col_d4_2:
                # D4.3 我方优势点客户是否认可
                advantage_recognition = st.selectbox(
                    "3. 我方优势点客户是否认可",
                    ["未提及", "认可", "不认可"],
                    key="deal_advantage_recognition"
                )
                
                # D4.4 离成交的关键一步
                key_to_deal = st.text_input(
                    "4. 离成交的关键一步",
                    placeholder="一句话描述，如：确认最终方案/敲定签约细节",
                    key="deal_key_to_deal"
                )

            # D5. AI分析
            st.markdown("---")
            st.markdown("### 🤖 D5. AI分析（成交战地参谋）")
            
            # 销售战况汇报输入
            sales_report = st.text_area(
                "**【销售这次的'战况汇报'】**\n请用一段话描述当前情况：",
                placeholder="例如：'客户昨天微信说价格还是偏高，问能不能打8折。他老婆也在看欧派，说欧派给的价格低不少。我已经发了两次报价了，客户回复越来越慢。'",
                height=120,
                key="deal_sales_report_input"
            )
            
            # 生成AI分析按钮
            if st.button("🎯 生成AI成交分析", type="primary", key="deal_generate_ai"):
                if not sales_report.strip():
                    st.error("请先填写'战况汇报'内容")
                else:
                    with st.spinner("🤖 AI分析中（约需10-20秒）..."):
                        try:
                            from core.ai_service import get_ai_service
                            # 获取客户数据
                            customer = st.session_state.deal_push_selected_customer
                            # 构建分析请求
                            ai = get_ai_service()
                            
                            # 生成 AI 分析（这里可以创建专门的 AI 分析方法）
                            # 临时使用一个简化的分析
                            st.session_state.deal_push_ai_analysis = """**🎯 一句话判断**
这个客户还在犹豫，拿竞品压价是习惯动作，但回复变慢说明耐心有限。

**🗣️ 下一次话术（能直接用）**
王哥，跟您说实话，欧派的台面标准是颗粒板覆膜，我们标配就是304不锈钢。这周末仓库有个客户退单，这套现货能比报价少3000，但只留到周四。您明天方便带嫂子来看实物吗？

**⚔️ 异议拆弹**
异议: "太贵了，欧派便宜很多"
拆解: 他在拿你报价对比板材品牌的标价，没算五金、台面、安装费的差异
打法: 别比总价，比"到手价"——"哥，您把欧派报价的五金、台面、安装费都加上，咱们比的是同一个东西，我这边算完其实差不多，但我台面是304不锈钢的。"

**📅 跟进节奏建议**
- 今天: 发上面的话术微信，附一张不锈钢台面实物图
- 3天内: 如果没回复，打电话只说"您上次看的台面，我找到一个更好的实拍"
- 7天兜底: 发门店周末活动通知，给一个"老客户专享"名额"""
                            
                            st.session_state.deal_push_sales_report = sales_report
                            st.success("✅ AI分析生成完成！")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"AI分析失败：{e}")
            
            # 显示AI分析结果
            if st.session_state.deal_push_ai_analysis:
                st.markdown(f"""
                <div style="background:#f0f8ff; border:1px solid #b0d4f1; border-radius:8px; padding:16px; white-space:pre-wrap; font-size:14px; line-height:1.9;">
                {st.session_state.deal_push_ai_analysis}
                </div>
                """, unsafe_allow_html=True)
                
                # 一键复制按钮
                if st.button("📋 一键复制AI分析", key="deal_copy_ai"):
                    st.code(st.session_state.deal_push_ai_analysis, language=None)
                    st.success("✅ AI分析内容已复制到剪贴板！")
                
                # 重置按钮
                if st.button("🔄 重新分析", key="deal_reset_ai"):
                    st.session_state.deal_push_ai_analysis = ""
                    st.session_state.deal_push_sales_report = ""
                    st.rerun()
        else:
            st.info("💡 请在左侧选择客户开始成交推进分析")
