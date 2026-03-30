"""
成交魔方 V3 - 客户诊断引擎
结构化采集需求，输出客户画像、预算敏感度、风格倾向与成交风险
"""

import uuid
import logging
import streamlit as st
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def generate_customer_no() -> str:
    """生成顾客编号，格式：MC-YYYYMMDD-XXXX"""
    today = date.today().strftime("%Y%m%d")
    suffix = str(uuid.uuid4())[:4].upper()
    return f"MC-{today}-{suffix}"


def show_customer_diagnosis_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">🎯 客户诊断</h2>
        <p style="margin:4px 0 0 0; color:#666;">结构化采集需求，输出客户画像、预算敏感度、风格倾向与成交风险</p>
    </div>
    """, unsafe_allow_html=True)

    # 初始化 session state
    if "diag_customer_no" not in st.session_state:
        st.session_state.diag_customer_no = generate_customer_no()
    if "diag_card_result" not in st.session_state:
        st.session_state.diag_card_result = ""
    if "diag_detail_result" not in st.session_state:
        st.session_state.diag_detail_result = ""

    tab1, tab2, tab3 = st.tabs(["📋 客户信息录入", "🤖 AI 分析结果", "📊 客户记录列表"])

    # ============================================================
    # TAB 1 - 表单录入
    # ============================================================
    with tab1:
        with st.form("customer_diagnosis_form", clear_on_submit=False):

            # ── A. 客户画像 & 项目概况 ──────────────────────────
            st.markdown("### 🅰️ 客户画像 & 项目概况")
            col1, col2 = st.columns(2)
            with col1:
                customer_name = st.text_input("1. 客户姓名 *", placeholder="请输入姓名")
                contact = st.text_input("2. 联系方式（电话/微信，至少一种）*", placeholder="手机号或微信号")
                customer_no = st.text_input(
                    "3. 顾客编号（自动生成）",
                    value=st.session_state.diag_customer_no,
                    disabled=True
                )
                age_range = st.selectbox(
                    "4. 年龄段",
                    ["未知", "30以下", "31-40", "41-50", "51+"]
                )
                visit_count = st.selectbox(
                    "5. 到店次数",
                    ["首次", "二次", "三次以上"]
                )
                source_channel = st.selectbox(
                    "6. 来源渠道",
                    ["自然进店", "转介绍", "线上", "渠道合作", "社区拓客", "老客复购"]
                )
                source_note = st.text_input(
                    "7. 来源备注（可选）",
                    placeholder="如：抖音/小红书/设计师/老客户姓名"
                )

            with col2:
                house_type = st.selectbox(
                    "8. 房屋类型",
                    ["未知", "普通住宅", "改善型住宅", "别墅大宅", "公寓商住", "自建房"]
                )
                house_area = st.text_input("9. 房屋区域", placeholder="如：万科城、碧桂园一期")
                renovation_type = st.selectbox(
                    "10. 装修类型",
                    ["未明确", "新装", "全屋翻新", "局部改造", "已入住换柜"]
                )
                renovation_stage = st.selectbox(
                    "11. 装修阶段",
                    ["未开始", "设计中", "拆改水电", "硬装完成", "已入住改造"]
                )
                order_timeline = st.selectbox(
                    "12. 预计下单时间",
                    ["不明确", "1周内", "2周内", "1个月内", "1-3个月", "3个月后"]
                )
                custom_spaces = st.multiselect(
                    "13. 定制空间（可多选）",
                    ["橱柜", "餐边柜", "厅柜", "鞋柜", "家政柜", "衣柜", "浴室柜", "其他"]
                )
                budget_range = st.selectbox(
                    "14. 定制预算",
                    ["未透露", "5万以下", "5-10万", "10-20万", "20-30万", "30万以上"]
                )

            st.markdown("---")
            # ── B. 决策链 & 跟进路径 ─────────────────────────────
            st.markdown("### 🅱️ 决策链 & 跟进路径")
            col3, col4 = st.columns(2)
            with col3:
                visitor_identity = st.selectbox(
                    "1. 当前到店身份",
                    ["不明确", "主决策人本人", "主决策人的配偶", "主决策人的父母", "影响者", "使用者", "代看"]
                )
                decision_maker = st.selectbox(
                    "2. 最终拍板人",
                    ["不明确", "本人", "配偶", "父母", "共同决定"]
                )
                companion_type = st.multiselect(
                    "3. 同行角色（可多选）",
                    ["配偶", "父母", "孩子", "朋友", "设计师", "装修师傅", "其他"]
                )
            with col4:
                next_step = st.selectbox(
                    "4. 下一步计划",
                    ["加微信跟进", "邀约二次到店", "预约上门测量", "待客户发户型图", "待决策人到店", "暂不跟进"]
                )
                next_followup_date = st.date_input(
                    "5. 下次跟进时间",
                    value=date.today() + timedelta(days=3),
                    min_value=date.today()
                )

            st.markdown("---")
            # ── C. 需求与偏好标签 ─────────────────────────────────
            st.markdown("### 🅲 需求与偏好标签")
            col5, col6 = st.columns(2)
            with col5:
                style_preference = st.multiselect(
                    "1. 风格倾向（最多选2）",
                    ["现代简约", "轻奢", "新中式", "原木自然", "极简灰系", "其他"],
                    max_selections=2
                )
                appearance_preference = st.multiselect(
                    "2. 外观质感倾向（最多选3）",
                    ["烤漆", "实木", "转印纹理", "玻璃", "岩板", "石材", "暂未明确"],
                    max_selections=3
                )
                material_type_preference = st.multiselect(
                    "3. 板材材质倾向（最多选2）",
                    ["不锈钢", "实木", "颗粒板", "多层板", "欧松板", "暂未明确"],
                    max_selections=2
                )
                focus_points = st.multiselect(
                    "4. 最关注点（最多选3）",
                    ["颜值设计", "收纳实用", "环保健康", "耐用性", "性价比", "易清洁打理", "智能功能", "品牌/售后"],
                    max_selections=3
                )
            with col6:
                compare_brands_yn = st.radio(
                    "5. 是否对比其他品牌",
                    ["否", "是"],
                    horizontal=True
                )
                compare_brands = ""
                if compare_brands_yn == "是":
                    compare_brands = st.text_input("对比品牌名称", placeholder="如：欧派、索菲亚")
                family_size = st.selectbox(
                    "6. 家庭人数",
                    ["未知", "1-2人", "3-4人", "5人以上"]
                )

            st.markdown("---")
            # ── 提交按钮 ─────────────────────────────────────────
            # ── 提交按钮 ─────────────────────────────────────────
            col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
            with col_s2:
                submitted = st.form_submit_button(
                    "💾 保存客户信息 + 生成AI分析",
                    type="primary",
                    use_container_width=True
                )

            # ── 表单提交处理 ──────────────────────────────────────
            if submitted:
                # 基本校验
                if not customer_name.strip():
                    st.error("❌ 请填写客户姓名")
                    st.stop()
                if not contact.strip():
                    st.error("❌ 请填写联系方式")
                    st.stop()

                # 组装数据
                customer_data = {
                    "customer_name": customer_name.strip(),
                    "contact": contact.strip(),
                    "customer_no": customer_no,
                    "age_range": age_range,
                    "visit_count": visit_count,
                    "source_channel": source_channel,
                    "source_note": source_note.strip(),
                    "house_type": house_type,
                    "house_area": house_area.strip(),
                    "renovation_type": renovation_type,
                    "renovation_stage": renovation_stage,
                    "order_timeline": order_timeline,
                    "custom_spaces": custom_spaces,
                    "budget_range": budget_range,
                    "visitor_identity": visitor_identity,
                    "decision_maker": decision_maker,
                    "companion_type": companion_type,
                    "next_step": next_step,
                    "next_followup_date": next_followup_date.isoformat(),
                    "style_preference": style_preference,
                    "appearance_preference": appearance_preference,
                    "material_type_preference": material_type_preference,
                    "focus_points": focus_points,
                    "compare_brands": compare_brands if compare_brands_yn == "是" else "否",
                    "family_size": family_size,
                }

                # 保存到数据库
                try:
                    from core.database import db
                    # 映射到数据库字段
                    db_data = customer_data.copy()
                    record_id = db.insert("customers_v3", db_data)
                    st.success(f"✅ 客户信息已保存！编号：{customer_no}，ID：{record_id}")
                except Exception as e:
                    st.warning(f"⚠️ 数据库保存失败（{str(e)[:60]}），AI分析仍可正常使用")

                # 保存到 session state，切换到 AI 分析 Tab 时使用
                st.session_state.diag_customer_data = customer_data
                st.session_state.diag_card_result = ""
                st.session_state.diag_detail_result = ""

                # 调用 AI 主卡分析
                with st.spinner("🤖 正在生成 AI 分析（主卡）..."):
                    try:
                        from core.ai_service import get_ai_service
                        ai = get_ai_service()
                        card = ai.analyze_card(customer_data)
                        st.session_state.diag_card_result = card
                        st.success("✅ AI 主卡分析完成！请切换到「AI 分析结果」标签查看")
                    except Exception as e:
                        st.error(f"❌ AI 分析失败：{str(e)}")

                # 刷新顾客编号，准备下一个客户
                st.session_state.diag_customer_no = generate_customer_no()

    # ============================================================
    # TAB 2 - AI 分析结果
    # ============================================================
    with tab2:
        if not st.session_state.get("diag_customer_data"):
            st.info("💡 请先在「客户信息录入」Tab 填写并提交客户信息")
            return

        customer_data = st.session_state.diag_customer_data
        card_result = st.session_state.get("diag_card_result", "")

        # 客户基本信息概览
        st.markdown(f"""
        <div style="background:#f8f9fa; border-left:4px solid #d4af37; padding:12px 16px; border-radius:4px; margin-bottom:16px;">
            <strong>当前客户：</strong>{customer_data.get('customer_name', '-')} &nbsp;|&nbsp;
            <strong>编号：</strong>{customer_data.get('customer_no', '-')} &nbsp;|&nbsp;
            <strong>预算：</strong>{customer_data.get('budget_range', '-')} &nbsp;|&nbsp;
            <strong>意向：</strong>{customer_data.get('intent_level', '-')}
        </div>
        """, unsafe_allow_html=True)

        # ── 主卡（销售必看）──────────────────────────────────────
        st.markdown("### 📌 主卡分析（销售必看）")
        if card_result:
            st.markdown(f"""
            <div style="background:#fffef0; border:1px solid #f0e68c; border-radius:8px; padding:16px; white-space:pre-wrap; font-size:15px; line-height:1.8;">
{card_result}
            </div>
            """, unsafe_allow_html=True)
            # 一键复制主卡
            col_copy1, col_regen1 = st.columns([1, 1])
            with col_copy1:
                st.code(card_result, language=None)
            with col_regen1:
                if st.button("🔄 重新生成主卡", key="regen_card"):
                    st.session_state.diag_card_result = ""
                    st.rerun()
            st.caption("💡 点击上方代码框右上角的复制图标，即可一键复制全文")
        else:
            if st.button("▶ 生成主卡分析", type="primary"):
                with st.spinner("🤖 分析中..."):
                    try:
                        from core.ai_service import get_ai_service
                        ai = get_ai_service()
                        card = ai.analyze_card(customer_data)
                        st.session_state.diag_card_result = card
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {str(e)}")

        # ── 详情分析 ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔍 详情分析（五大板块）")
        detail_result = st.session_state.get("diag_detail_result", "")
        if detail_result:
            # 只显示一个卡片，不重复渲染
            st.markdown(f"""
            <div style="background:#f0f8ff; border:1px solid #b0d4f1; border-radius:8px; padding:16px; white-space:pre-wrap; font-size:14px; line-height:1.9;">
{detail_result}
            </div>
            """, unsafe_allow_html=True)
            
            # 一键复制按钮（在卡片下方）
            if st.button("📋 一键复制详情分析", key="copy_detail"):
                st.code(detail_result, language=None)
                st.success("✅ 详情分析内容已复制到剪贴板！")
            
            if st.button("🔄 重新生成详情分析", key="regen_detail"):
                st.session_state.diag_detail_result = ""
                st.rerun()
        else:
            if card_result:
                if st.button("▶ 展开详情分析", type="secondary"):
                    with st.spinner("🤖 深度分析中（约需10-20秒）..."):
                        try:
                            from core.ai_service import get_ai_service
                            ai = get_ai_service()
                            detail = ai.analyze_detail(customer_data, card_result)
                            st.session_state.diag_detail_result = detail
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {str(e)}")
            else:
                st.info("💡 请先生成主卡分析，再展开详情分析")

        # ── 跳转方案引导（A → B 打通） ───────────────────────────
        if card_result:
            st.markdown("---")
            col_go, _ = st.columns([2, 3])
            with col_go:
                if st.button(
                    "🎨 进入方案引导 →",
                    type="primary",
                    use_container_width=True,
                    key="goto_solution_guide",
                    help="将当前客户数据传导到「方案引导」板块，生成设计方案分析"
                ):
                    # 把 AI 分析结果也存到客户数据里，供方案引导的①传导块显示
                    customer_with_ai = st.session_state.diag_customer_data.copy()
                    customer_with_ai["ai_card_result"] = card_result
                    st.session_state.diag_customer_data = customer_with_ai
                    st.session_state["current_page"] = "方案引导"
                    st.rerun()

    # ============================================================
    # TAB 3 - 客户记录列表
    # ============================================================
    with tab3:
        st.markdown("### 📊 客户记录列表")

        # 筛选栏
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
        with col_f1:
            filter_intent = st.selectbox("意向等级", ["全部", "高", "中", "低"], key="list_filter_intent")
        with col_f2:
            filter_days = st.selectbox("时间范围", ["全部", "今天", "近3天", "近7天", "近30天"], key="list_filter_days")
        with col_f3:
            filter_name = st.text_input("搜索姓名", placeholder="输入客户姓名", key="list_filter_name")
        with col_f4:
            st.markdown("<br>", unsafe_allow_html=True)
            refresh_btn = st.button("🔄 刷新", use_container_width=True, key="list_refresh")

        # 加载数据
        try:
            from core.database import db
            from datetime import datetime

            # 调试：打印数据库查询结果
            st.markdown("### 🔍 调试信息")
            with st.expander("查看数据库查询详情（调试用）"):
                try:
                    raw_customers = db.select("customers_v3", order_by="created_at.desc", limit=200)
                    st.write(f"**原始查询结果数量：** {len(raw_customers)}")
                    if raw_customers:
                        st.write("**第一条记录数据：**")
                        st.json(raw_customers[0])
                    else:
                        st.warning("数据库返回空列表")
                except Exception as debug_e:
                    st.error(f"数据库查询异常：{debug_e}")
                    import traceback
                    st.code(traceback.format_exc())

            customers = db.select("customers_v3", order_by="created_at.desc", limit=200)

            # 本地筛选
            if filter_intent != "全部":
                customers = [c for c in customers if c.get("intent_level", "") == filter_intent]
            if filter_name.strip():
                customers = [c for c in customers if filter_name.strip() in (c.get("customer_name") or "")]
            if filter_days != "全部":
                days_map = {"今天": 1, "近3天": 3, "近7天": 7, "近30天": 30}
                cutoff = datetime.now() - timedelta(days=days_map[filter_days])
                def _in_range(c):
                    ts = c.get("created_at", "")
                    if not ts:
                        return False
                    try:
                        t = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                        return t >= cutoff
                    except Exception:
                        return True
                customers = [c for c in customers if _in_range(c)]

            if not customers:
                st.info("暂无客户记录，快去录入第一个客户吧！")
            else:
                # 统计卡片
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                total_count = len(customers)
                high_count = sum(1 for c in customers if c.get("intent_level") == "高")
                mid_count = sum(1 for c in customers if c.get("intent_level") == "中")
                low_count = sum(1 for c in customers if c.get("intent_level") == "低")

                with col_m1:
                    st.metric("总客户数", total_count)
                with col_m2:
                    st.metric("🟢 高意向", high_count)
                with col_m3:
                    st.metric("🟡 中意向", mid_count)
                with col_m4:
                    st.metric("🔴 低意向", low_count)

                st.markdown("---")
                st.markdown(f"共 **{len(customers)}** 条记录")

                # 表格
                import pandas as pd

                # 意向标签颜色
                intent_badge = {
                    "高": "🟢 高意向",
                    "中": "🟡 中意向",
                    "低": "🔴 低意向",
                }

                table_data = []
                for idx, c in enumerate(customers):
                    intent = c.get("intent_level", "-")
                    badge = intent_badge.get(intent, f"⚪ {intent}")
                    name = c.get("customer_name", "-")
                    no = c.get("customer_no", "-")
                    budget = c.get("budget_range", "-")
                    source = c.get("source_channel", "-")
                    next_step = c.get("next_step", "-")
                    created = (c.get("created_at") or "")[:16].replace("T", " ")
                    ai_done = "✅" if c.get("ai_card_result") else "—"
                    spaces_raw = c.get("custom_spaces") or []
                    spaces = " / ".join(spaces_raw) if spaces_raw else "-"

                    table_data.append({
                        "客户姓名": name,
                        "意向": badge,
                        "客户编号": no,
                        "预算": budget,
                        "来源": source,
                        "定制空间": spaces,
                        "联系方式": c.get("contact", "-"),
                        "创建时间": created,
                        "AI分析": ai_done,
                        "操作": f"查看_{idx}",
                    })

                df = pd.DataFrame(table_data)

                # 自定义列宽
                column_config = {
                    "客户姓名": st.column_config.Column(width=100),
                    "意向": st.column_config.Column(width=100),
                    "客户编号": st.column_config.Column(width=140),
                    "预算": st.column_config.Column(width=100),
                    "来源": st.column_config.Column(width=100),
                    "定制空间": st.column_config.Column(width=150),
                    "联系方式": st.column_config.Column(width=120),
                    "创建时间": st.column_config.Column(width=150),
                    "AI分析": st.column_config.Column(width=80),
                    "操作": st.column_config.Column(width=120),
                }

                # 显示表格
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "客户姓名": st.column_config.Column(width=100),
                        "意向": st.column_config.Column(width=100),
                        "客户编号": st.column_config.Column(width=140),
                        "预算": st.column_config.Column(width=100),
                        "来源": st.column_config.Column(width=100),
                        "定制空间": st.column_config.Column(width=150),
                        "联系方式": st.column_config.Column(width=120),
                        "创建时间": st.column_config.Column(width=150),
                        "AI分析": st.column_config.Column(width=80),
                        "操作": st.column_config.SelectboxColumn(
                            "操作",
                            width=150,
                            options=["选择操作", "查看详情", "删除记录", "加载分析"],
                            required=True
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="customer_table_editor",
                )

                # 处理操作
                for i, row in edited_df.iterrows():
                    if i < len(customers):
                        customer_id = customers[i].get("id")
                        customer_name = customers[i].get("customer_name", "未知")
                        action = row.get("操作")
                        
                        if action == "查看详情":
                            st.session_state.selected_customer_idx = i
                            st.rerun()
                        elif action == "删除记录":
                            if customer_id:
                                try:
                                    from core.database import db
                                    db.delete("customers_v3", customer_id)
                                    st.success(f"✅ 已删除客户「{customer_name}」")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"删除失败：{e}")
                            else:
                                st.warning("无法获取客户ID")
                            st.rerun()
                        elif action == "加载分析":
                            c = customers[i]
                            st.session_state.diag_customer_data = c
                            st.session_state.diag_card_result = c.get("ai_card_result", "")
                            st.session_state.diag_detail_result = c.get("ai_detail_result", "")
                            st.session_state.current_page = "客户洞察"
                            st.success(f"✅ 已加载「{customer_name}」的数据，请切换到「AI 分析结果」标签")
                            st.rerun()

                # 详情展开（点击表格行后显示）
                if st.session_state.get("selected_customer_idx") is not None:
                    sel_idx = st.session_state["selected_customer_idx"]
                    if 0 <= sel_idx < len(customers):
                        c = customers[sel_idx]
                        st.markdown("---")
                        st.markdown("### 📋 客户详情")
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.markdown(f"**客户编号：** {c.get('customer_no', '-')}")
                            st.markdown(f"**客户姓名：** {c.get('customer_name', '-')}")
                            st.markdown(f"**联系方式：** {c.get('contact', '-')}")
                            st.markdown(f"**来源渠道：** {c.get('source_channel', '-')}")
                        with col_b:
                            st.markdown(f"**预算范围：** {c.get('budget_range', '-')}")
                            st.markdown(f"**装修阶段：** {c.get('renovation_stage', '-')}")
                            st.markdown(f"**下单时间：** {c.get('order_timeline', '-')}")
                            st.markdown(f"**决策人：** {c.get('decision_maker', '-')}")
                        with col_c:
                            st.markdown(f"**下一步：** {c.get('next_step', '-')}")
                            st.markdown(f"**跟进日期：** {c.get('next_followup_date', '-')}")
                            st.markdown(f"**AI 分析状态：** {'✅ 已完成' if c.get('ai_card_result') else '— 未分析'}")

                        if c.get("sales_note"):
                            st.markdown(f"**销售备注：** {c.get('sales_note')}")

                        st.markdown("---")
                        col_load, _ = st.columns([2, 3])
                        with col_load:
                            if st.button(f"🤖 加载此客户到分析", key=f"load_customer_detail_{sel_idx}", use_container_width=True):
                                st.session_state.diag_customer_data = c
                                st.session_state.diag_card_result = c.get("ai_card_result", "")
                                st.session_state.diag_detail_result = c.get("ai_detail_result", "")
                                st.session_state["selected_customer_idx"] = None
                                st.success(f"已加载「{c.get('customer_name')}」的数据，请切换到「AI 分析结果」标签")
                                st.rerun()

        except Exception as e:
            st.warning(f"⚠️ 无法加载客户记录（{str(e)[:80]}）")
            st.info("请确认数据库连接正常，或先录入几条客户数据")

