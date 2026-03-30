"""
成交魔方 V3 - 方案引导
基于客户洞察，生成设计方案建议与参考图
"""

import streamlit as st
import logging
import base64
import requests

logger = logging.getLogger(__name__)

# ── 设计师风格选项 ──────────────────────────────────────────────────
STYLE_OPTIONS = [
    "现代简约", "轻奢风", "新中式", "原木自然风", "极简灰系",
    "北欧风", "法式复古", "工业风", "美式乡村", "地中海风"
]

# ── 参考品牌选项 ────────────────────────────────────────────────────
BRAND_OPTIONS = [
    "欧派", "索菲亚", "尚品宅配", "好莱客", "维意", "顶固",
    "科凡", "梦天", "玛格", "德维尔", "IKEA", "宜家定制"
]


def _load_customer_from_db(customer_id: str) -> dict:
    """从数据库加载指定客户数据"""
    try:
        from core.database import db
        result = db.get_by_id("customers_v3", customer_id)
        return result or {}
    except Exception:
        return {}


def _get_customer_list() -> list:
    """获取最近的客户列表（用于下拉选择）"""
    try:
        from core.database import db
        customers = db.select("customers_v3", order_by="created_at.desc", limit=50)
        return customers or []
    except Exception:
        return []


def _generate_image(prompt: str, api_key: str, base_url: str, model: str) -> bytes | None:
    """调用 MIMO/OpenAI 兼容的图像生成 API"""
    try:
        url = f"{base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        img_url = data["data"][0]["url"]
        img_resp = requests.get(img_url, timeout=30)
        img_resp.raise_for_status()
        return img_resp.content
    except Exception as e:
        logger.error(f"生图失败: {e}")
        raise


def _build_design_prompt(customer: dict, designer_note: str,
                          styles: list, brands: list) -> str:
    """组装设计 AI 分析 Prompt"""
    spaces = "、".join(customer.get("custom_spaces") or []) or "未指定"
    budget = customer.get("budget_range", "未透露")
    style_pref = "、".join(customer.get("style_preference") or []) or "未指定"
    material = "、".join(customer.get("material_preference") or []) or "未指定"
    focus = "、".join(customer.get("focus_points") or []) or "未指定"
    house_type = customer.get("house_type", "未知")
    renovation = customer.get("renovation_type", "未知")
    special = customer.get("special_needs", "")

    ref_styles = "、".join(styles) if styles else "无特别指定"
    ref_brands = "、".join(brands) if brands else "无特别指定"

    prompt = f"""你是一个有15年经验的全屋定制设计顾问，现在请根据以下客户信息，给出具体可落地的方案引导建议。

【客户基本信息】
- 定制空间：{spaces}
- 预算范围：{budget}
- 房屋类型：{house_type}
- 装修类型：{renovation}
- 客户风格偏好：{style_pref}
- 材质偏好：{material}
- 最关注点：{focus}
- 特殊需求：{special or "无"}

【设计师补充/调整要求】
{designer_note or "无特别补充"}

【参考方向】
- 参考设计师风格：{ref_styles}
- 参考品牌风格：{ref_brands}

【请输出以下4个板块，每板块不超过120字】

═══ 1. 方案核心定位 ═══
用一句话概括这套方案的设计灵魂，比如："原木+哑光白的自然系轻奢，主打收纳与颜值并重"

═══ 2. 各空间方案建议 ═══
针对客户要定制的每个空间，给1-2句具体建议（材质/功能/细节），要听起来专业但客户能听懂

═══ 3. 重点卖点话术 ═══
给3条销售能直接说给客户听的话，突出差异化，让客户觉得"就是这个"

═══ 4. 生图参考关键词 ═══
给出3-5个适合用来生成效果图的英文关键词组合，格式：
keyword1, keyword2, keyword3, style: xxx, color: xxx, quality: high

【铁律】全程大白话，禁止堆砌术语，每个板块给判断和动作，不要废话
"""
    return prompt


def show_solution_guide_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">🎨 方案引导</h2>
        <p style="margin:4px 0 0 0; color:#666;">基于客户洞察，快速确认风格、功能、材质方向并生成设计参考</p>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # ① 客户洞察传导信息
    # ============================================================
    st.markdown("---")
    st.markdown("#### ① 客户洞察传导信息")

    # 优先使用从客户诊断跳转过来的数据
    customer = st.session_state.get("diag_customer_data") or {}

    # 如果没有，提供下拉选择
    if not customer:
        customers_list = _get_customer_list()
        if customers_list:
            options = {f"{c.get('customer_name','未知')} · {c.get('customer_no','')} · {c.get('intent_level','')}": c
                       for c in customers_list}
            selected_label = st.selectbox(
                "选择已录入的客户",
                ["— 请选择 —"] + list(options.keys()),
                key="sg_customer_select"
            )
            if selected_label != "— 请选择 —":
                customer = options[selected_label]
        else:
            st.info("💡 尚未录入任何客户。请先在「客户诊断」录入客户信息，或直接填写下方设计要求。")

    # 展示客户摘要卡
    if customer:
        name = customer.get("customer_name", "未知")
        intent = customer.get("intent_level", "-")
        budget = customer.get("budget_range", "-")
        stage = customer.get("renovation_stage", "-")
        spaces = "、".join(customer.get("custom_spaces") or []) or "-"
        style_pref = "、".join(customer.get("style_preference") or []) or "-"
        material = "、".join(customer.get("material_preference") or []) or "-"
        focus = "、".join(customer.get("focus_points") or []) or "-"
        special = customer.get("special_needs", "")

        intent_color = {"高": "#52c41a", "中": "#faad14", "低": "#ff4d4f"}.get(intent, "#999")

        with st.expander("▶ 客户洞察传导", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**客户**\n\n### {name}")
            c2.markdown(f"**意向**\n\n### <span style='color:{intent_color}'>{intent}意向</span>",
                        unsafe_allow_html=True)
            c3.markdown(f"**预算**\n\n### {budget}")
            c4.markdown(f"**装修阶段**\n\n### {stage}")

            st.markdown("---")
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"**定制空间：** {spaces}")
                st.markdown(f"**风格偏好：** {style_pref}")
                st.markdown(f"**材质偏好：** {material}")
            with col_r:
                st.markdown(f"**最关注点：** {focus}")
                st.markdown(f"**房屋类型：** {customer.get('house_type', '-')}")
                st.markdown(f"**装修类型：** {customer.get('renovation_type', '-')}")
            if special:
                st.markdown(f"**特殊需求：** {special}")
    else:
        st.caption("暂无客户数据，可直接填写下方设计要求进行方案分析")

    # ============================================================
    # ② 设计修正栏
    # ============================================================
    st.markdown("---")
    st.markdown("#### ② 设计修正栏")
    st.caption("设计师可在此补充或调整设计要求，优先级高于客户洞察自动传导内容")
    designer_note = st.text_area(
        "设计师备注 / 调整要求",
        placeholder="例如：客户现场补充了对厨房的特别要求；希望整体偏冷调；取消阳台柜改为榻榻米...",
        height=100,
        key="sg_designer_note"
    )

    # ============================================================
    # ③ 参考设计师风格
    # ============================================================
    st.markdown("---")
    st.markdown("#### ③ 参考设计师风格（可多选）")
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        selected_styles = st.multiselect(
            "选择参考风格",
            STYLE_OPTIONS,
            default=[],
            key="sg_styles"
        )
    with col_s2:
        custom_style = st.text_input("其他（自填）", placeholder="如：贝聿铭", key="sg_custom_style")
    if custom_style:
        selected_styles = selected_styles + [custom_style]

    # ============================================================
    # ④ 参考品牌
    # ============================================================
    st.markdown("---")
    st.markdown("#### ④ 参考品牌（可多选）")
    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        selected_brands = st.multiselect(
            "选择参考品牌",
            BRAND_OPTIONS,
            default=[],
            key="sg_brands"
        )
    with col_b2:
        custom_brand = st.text_input("其他（自填）", placeholder="如：De Padova", key="sg_custom_brand")
    if custom_brand:
        selected_brands = selected_brands + [custom_brand]

    # ============================================================
    # ⑤ 参考图上传（最多2张）
    # ============================================================
    st.markdown("---")
    st.markdown("#### ⑤ 参考图上传（最多2张）")
    st.caption("支持 JPG / PNG / WEBP · 边边 < 1680px · 大小 < 2MB")
    uploaded_files = st.file_uploader(
        "上传参考图",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="sg_ref_images"
    )
    if uploaded_files:
        cols = st.columns(min(len(uploaded_files), 2))
        for i, f in enumerate(uploaded_files[:2]):
            with cols[i]:
                st.image(f, use_container_width=True, caption=f.name)

    # ============================================================
    # ⑥ 生成 AI 设计分析
    # ============================================================
    st.markdown("---")
    st.markdown("#### ⑥ AI 设计方案分析")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        gen_analysis_btn = st.button("🤖 生成 AI 设计分析", type="primary", use_container_width=True, key="sg_gen_analysis")
    with col_btn2:
        gen_image_btn = st.button("🎨 AI 生成效果图", type="secondary", use_container_width=True, key="sg_gen_image")

    # 生成设计分析
    if gen_analysis_btn:
        with st.spinner("🤖 正在生成设计方案分析..."):
            try:
                from core.ai_service import get_ai_service
                ai = get_ai_service()
                prompt_text = _build_design_prompt(
                    customer or {},
                    designer_note,
                    selected_styles,
                    selected_brands
                )
                # 直接调用 chat 接口
                client = ai.client
                resp = client.chat.completions.create(
                    model=ai.model,
                    messages=[
                        {"role": "system", "content": "你是一个有15年经验的全屋定制设计顾问，擅长用大白话给销售提供方案引导建议。"},
                        {"role": "user", "content": prompt_text}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )
                result = resp.choices[0].message.content.strip()
                st.session_state.sg_analysis_result = result
                st.rerun()
            except Exception as e:
                st.error(f"❌ AI 分析失败：{str(e)}")

    # 展示设计分析结果
    analysis_result = st.session_state.get("sg_analysis_result", "")
    if analysis_result:
        st.markdown("""
        <div style="background:#f0fff4; border:1px solid #b7eb8f; border-radius:8px; padding:4px 8px; margin-bottom:4px;">
            <strong>🎨 AI 设计方案分析</strong>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#f6ffed; border:1px solid #b7eb8f; border-radius:8px; padding:16px; white-space:pre-wrap; font-size:14px; line-height:1.9;">
{analysis_result}
        </div>
        """, unsafe_allow_html=True)
        st.code(analysis_result, language=None)
        st.caption("💡 点击上方代码框右上角复制图标，一键复制分析结果")

    # ============================================================
    # ⑦ AI 生成效果图
    # ============================================================
    if gen_image_btn:
        # 从分析结果里提取关键词，或用基础 prompt
        image_prompt = ""
        if analysis_result and "keyword" in analysis_result.lower():
            # 尝试提取第 4 板块的关键词
            lines = analysis_result.split("\n")
            for i, line in enumerate(lines):
                if "生图" in line or "keyword" in line.lower():
                    # 取下一行非空内容
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip():
                            image_prompt = lines[j].strip()
                            break
                    break

        if not image_prompt:
            # 用基础信息组合 prompt
            spaces = "、".join(customer.get("custom_spaces") or []) if customer else "living room"
            styles_str = ", ".join(selected_styles) if selected_styles else "modern minimalist"
            image_prompt = (
                f"full house custom furniture design, {styles_str}, "
                f"Chinese home interior, high quality render, "
                f"4K photorealistic, warm lighting, clean layout"
            )

        with st.spinner("🎨 正在生成效果图（约20-30秒）..."):
            try:
                from core.config import config
                img_bytes = _generate_image(
                    prompt=image_prompt,
                    api_key=config.ai.api_key,
                    base_url=config.ai.base_url,
                    model="dall-e-3"   # 可在配置中覆盖
                )
                st.session_state.sg_generated_image = img_bytes
                st.session_state.sg_image_prompt = image_prompt
                st.rerun()
            except Exception as e:
                st.warning(f"⚠️ 生图接口暂不可用：{str(e)[:80]}")
                st.info("💡 生图功能需要 API 支持 `/images/generations` 接口（如 DALL·E 3 / 硅基流动 / 智谱 CogView）。\n\n如当前 API 不支持，可在下方手动输入生图关键词，到 Midjourney / 即梦 / 可灵等平台生成。")

                # 降级：展示关键词供手动使用
                st.markdown("**📋 生图参考关键词（可复制到 Midjourney / 即梦）：**")
                st.code(image_prompt, language=None)

    # 展示已生成的图
    if st.session_state.get("sg_generated_image"):
        st.markdown("---")
        st.markdown("#### 🖼️ AI 生成效果图")
        st.image(st.session_state.sg_generated_image, use_container_width=True)
        st.caption(f"生图 Prompt：{st.session_state.get('sg_image_prompt', '')}")

        # 下载按钮
        st.download_button(
            label="⬇️ 下载效果图",
            data=st.session_state.sg_generated_image,
            file_name="design_preview.png",
            mime="image/png"
        )
        if st.button("🔄 重新生成", key="sg_regen_image"):
            st.session_state.sg_generated_image = None
            st.session_state.sg_image_prompt = ""
            st.rerun()
