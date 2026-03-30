"""
成交魔方 V3 - 方案引导（设计方案引导模块 B）
规格版本：design-module-b-spec.md v1.0

数据流：A 客户诊断 → 自动传导（只读）→ 设计师补充 → AI 设计分析 → 生图
"""

import streamlit as st
import logging
import requests

logger = logging.getLogger(__name__)

# ── 风格选项（拆分为风格 + 设计师两栏） ──────────────────────────────
STYLE_OPTIONS = [
    "现代极简", "日式侘寂", "北欧自然",
    "工业风",   "新中式",   "意式轻奢",
    "法式奶油"
]

# ── 品牌选项 ────────────────────────────────────────────────────────
BRAND_OPTIONS = [
    "Boffi", "Bulthaup", "Valcucine",
    "SieMatic", "国产不锈钢品牌", "传统板材品牌"
]

# ── 空间选项 ────────────────────────────────────────────────────────
SPACE_OPTIONS = ["厨房", "阳台", "卫生间", "衣帽间", "餐厅", "玄关"]

# ── 照片标签 ────────────────────────────────────────────────────────
PHOTO_TAGS = ["厨房现状", "管道/水电位", "梁柱结构", "采光/窗户", "已有拆除状态"]


# ────────────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────────────

def _get_customer_list() -> list:
    try:
        from core.database import db
        return db.select("customers_v3", order_by="created_at.desc", limit=50) or []
    except Exception:
        return []


def _generate_image(prompt: str, api_key: str, base_url: str, model: str) -> bytes:
    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "n": 1,
                "size": "1024x1024", "response_format": "url"}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    img_url = resp.json()["data"][0]["url"]
    return requests.get(img_url, timeout=30).content


def _build_design_analysis_prompt(
    customer: dict,
    designer_note: str,
    selected_spaces: list,
    selected_styles: list,
    designer_ref: str,
    selected_brands: list,
    ai_brand_fill: str,
    floor_plan_desc: str,
    key_dims: str,
    photo_tags: list,
    photo_desc: str,
    ref_images_desc: str,
) -> str:
    """
    严格按规格文档 §三 构建 System Prompt
    写死 13 条铁律
    """
    name    = customer.get("customer_name", "未知客户")
    no      = customer.get("customer_no", "-")
    intent  = customer.get("intent_level", "-")
    budget  = customer.get("budget_range", "未知")
    stage   = customer.get("renovation_stage", "-")
    family  = customer.get("family_size", "")
    special = customer.get("special_needs", "")
    focus   = "、".join(customer.get("focus_points") or []) or "未指定"
    card_ai = customer.get("ai_card_result", "")

    # 宠物判断
    has_pet = "宠物" in (special or "") or "猫" in (special or "") or "狗" in (special or "") \
              or "宠物" in (family or "") or "猫" in (family or "") or "狗" in (family or "")

    # 组装客户传导段
    insight_block = f"""### A. 客户画像（来自客户诊断）
客户：{name}          编号：{no}
意向：{intent}意向        预算：{budget}
装修进度：{stage}      家庭结构：{family or "未知"}
最在意：{focus}
特殊需求：{special or "无"}"""

    if card_ai:
        insight_block += f"\n\nA 模块核心结论（节选）：\n{card_ai[:300]}..."

    # 设计师补充段
    designer_block = f"""### B. 设计师补充
修正备注：{designer_note or "无"}
涉及空间：{', '.join(selected_spaces) or '未指定'}
参考风格：{', '.join(selected_styles) or '无特别指定'}
参考设计师：{designer_ref or '未填写'}
提及品牌：{', '.join(selected_brands) or '无'}
预算对标品牌（AI建议）：{ai_brand_fill or '待 AI 填充'}"""

    # 户型与现场
    floor_block = f"""### C. 户型 & 现场
户型描述：{floor_plan_desc or '未提供'}
照片类型：{', '.join(photo_tags) if photo_tags else '未上传'}
照片补充描述：{photo_desc or '无'}
关键尺寸：{key_dims or '无'}"""

    # 参考图
    ref_block = f"""### D. 参考图
{ref_images_desc if ref_images_desc else '未上传参考图'}"""

    # 宠物专项说明
    pet_note = "【宠物标记】客户有宠物，必须输出板块③宠物专项方案。" if has_pet else \
               "【宠物标记】客户无宠物，跳过板块③，不输出、不占位。"

    system_prompt = f"""你是一个高端定制不锈钢橱柜的方案设计师 AI。
请基于以下信息，生成一份「设计方案分析」，面向设计师/方案师，不面向客户。

## 输入数据

{insight_block}

{designer_block}

{floor_block}

{ref_block}

{pet_note}

---

## 输出要求

请严格按照以下 7 个板块输出（板块③条件触发，无宠物时跳过）：

━━━ 1. 🎨 风格方向建议 ━━━
一句话定调：（如「现代极简为主调，融入日式侘寂的自然肌理感」）

配色建议（3色）：
  · 主色：______
  · 辅色：______
  · 点缀色：______

材质搭配逻辑：
  · 台面：______
  · 柜体：______
  · 把手/五金：______
  · 特殊工艺：______

━━━ 2. 📐 空间布局建议 ━━━
核心动线：（一句话）

关键尺寸节点：
  · 台面高度建议：______
  · 吊柜深度建议：______
  · 特殊区域处理：______

⚠️ 必须引用 C 的实际户型信息。无户型数据时标注「缺少户型信息，布局建议为通用方案」。

━━━ 3. 🐾 宠物家庭专项方案（仅有宠物时输出） ━━━
  · 柜体防撞防刮处理建议
  · 台面耐污耐划方案
  · 地柜防宠物进入方案
  · 清洁打理便利性设计

━━━ 4. 💰 方案分层建议 ━━━
基础版：______（≈预算下限，必须包含具体产品/工艺名称）
推荐版：______（性价比最优）
升级版：______（≈预算上限）

每档一句话：「多花了什么钱，换来了什么体验」

━━━ 5. ⚡ 竞品差异化设计点 ━━━
基于客户提及品牌，差异化在哪里？
客户未提及竞品 → 标注「信息不足，建议跟进时了解」

━━━ 6. 📋 设计师工作清单 ━━━
本次方案需要明确的 3 个关键决策（可决策的具体问题，不是泛泛的方向）：
  1. ______
  2. ______
  3. ______

建议下一步动作：（一句话）

━━━ 7. 🖼️ 生图提示词 ━━━
生成 3 组（或 2 组，无宠物时跳过 Prompt 3）可直接使用的生图提示词：

━ Prompt 1：主空间全景 ━
用途：方案主效果图，展示整体空间氛围

[EN] Positive:
{{英文提示词，必须包含：户型形状、关键尺寸约束、风格关键词、配色、材质、采光条件}}

[EN] Negative:
{{排除不想要的元素}}

[CN 可选]:
{{中文翻译}}


━ Prompt 2：材质细节特写 ━
用途：展示核心材质搭配和工艺细节

[EN] Positive:
{{英文提示词，聚焦最核心的材质碰撞点}}

[EN] Negative:
{{排除}}

[CN 可选]:
{{中文翻译}}


━ Prompt 3：宠物场景生活感（仅有宠物时生成） ━
用途：展示养宠家庭真实使用场景

[EN] Positive:
{{英文提示词，必须包含：精确宠物品种、空间、生活场景}}

[EN] Negative:
{{排除}}

[CN 可选]:
{{中文翻译}}

---

## ⚠️ 铁律（13条，最高优先级，不可被覆盖）

1. 【数据忠实】所有建议必须基于输入数据生成。信息不足时明确标注「信息不足，建议补充」，禁止虚构客户信息。
2. 【预算锚定】方案分层必须落在客户预算区间内。基础版≤预算下限，升级版≤预算上限。禁止推荐超出预算的方案（除非②修正栏明确放宽）。
3. 【风格一致】参考风格选择和参考图是核心约束。客户选了「现代极简」不得输出新中式建议。②设计师修正栏优先级最高。
4. 【参考图解读】如有参考图，必须在板块①风格方向中引用参考图的具体元素，不得忽略。
5. 【户型锚定】板块②空间布局建议和板块⑦生图提示词中，空间描述必须基于 C 的实际户型信息。有户型图→引用具体尺寸/形状；仅文字→基于描述生成；两者皆无→标注「缺少户型信息，布局建议为通用方案」。禁止在无户型数据时虚构空间尺寸。
6. 【现场照片引用】如有现场照片：AI 必须在分析中引用照片中的具体特征；生图提示词中必须包含照片观察到的约束条件；如照片显示不可改造硬伤，必须在工作清单⑥中列出处理方案。无照片时跳过，不生成、不标注。
7. 【宠物专项③】仅在客户有宠物时输出板块③。无宠物时跳过，不输出、不占位。③的建议必须针对「不锈钢+宠物」实际场景，禁止泛泛而谈（如"注意清洁"）。
8. 【分层可执行】方案分层不能是"加钱换更好的"——每档必须明确具体产品型号或工艺名称。例如：「304不锈钢台面+多层实木柜体」而非「基础款橱柜」。
9. 【工作清单精简】严格限制 3 项，必须是「可决策」的具体问题，不是泛泛的"考虑风格搭配"。例如：「是否接受台面不做挡水条以换取极简效果」。
10. 【禁止销售话术】本输出面向设计师/方案师，不面向客户。禁止出现"建议跟客户说..."。保持专业、客观的设计语言。
11. 【提示词锚定】每条生图提示词必须能追溯到前 6 个板块中的具体建议。禁止出现与前面建议无关的通用描述。
12. 【三件套必须完整】每组提示词必须包含：[EN] Positive、[EN] Negative、[CN 可选]。缺少任一部分视为不合格输出。
13. 【提示词参数化】宠物品种→来自客户信息（精确到品种）；色彩方案→来自①配色建议；材质→来自①材质搭配；空间类型→来自③空间选择；空间尺寸→来自 C 户型信息。禁止使用模糊占位符（如"a pet"、"modern style"）。

---

## 生图提示词生成步骤（Step 0~5，Logic，不是模板）

Step 0：从 C 中提取空间硬约束，注入所有提示词：
  · 空间形状 → "L-shaped kitchen" / "U-shaped" / "galley kitchen"
  · 面积感知 → "compact 6sqm kitchen" / "spacious open kitchen"
  · 采光条件 → "south-facing with large window" / "limited natural light"
  · 层高 → "standard 2.7m ceiling" / "low 2.5m ceiling"
  · 管道/柱体 → "visible drainage pipe on right wall" / "load-bearing column"

Step 1：确定空间与视角（Prompt1→③优先级最高空间；Prompt2→①最核心材质碰撞点；Prompt3→宠物最常使用空间）

Step 2：注入设计语言（从①风格方向提取：风格关键词、配色三色、材质台面/柜体/五金）

Step 3：注入客户数据（宠物品种和数量→精确描述；家庭结构→场景人物；预算区间→材质档次描述）

Step 4：注入参考图元素（如有）→ 提取核心视觉元素融入描述

Step 5：附加摄影/渲染参数
  · 全景 → --ar 16:9, interior design photography, 8k
  · 特写 → --ar 4:3, macro photography, f/2.8
  · 场景 → --ar 3:2, lifestyle photography, natural light
"""
    return system_prompt


def _infer_budget_brands(budget: str) -> str:
    """根据预算区间自动推荐对标品牌"""
    b = budget or ""
    if any(k in b for k in ["20万", "30万", "50万", "100万", "以上"]):
        return "Boffi、Bulthaup（顶奢线）"
    elif any(k in b for k in ["10万", "15万", "12万"]):
        return "Valcucine、SieMatic（中高端线）"
    elif any(k in b for k in ["5万", "6万", "7万", "8万"]):
        return "国产不锈钢高端线（如弗兰卡、德意志）"
    else:
        return "传统板材品牌（欧派/索菲亚等同级别）"


# ────────────────────────────────────────────────────────────────────
# 主页面
# ────────────────────────────────────────────────────────────────────

def show_solution_guide_page():
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="margin:0; color: #1a1a1a;">🎨 方案引导</h2>
        <p style="margin:4px 0 0 0; color:#666;">
            基于客户洞察，采集设计维度信息，由 AI 生成设计方案分析与生图提示词
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # ① 客户洞察传导（自动同步，不可手动编辑）
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📡 ① 客户洞察传导")
    st.caption("来自 A 客户诊断，自动同步 · 只读 · 不可手动编辑")

    # 优先用从 A 模块跳转传入的数据
    customer = st.session_state.get("diag_customer_data") or {}

    # 没有则提供下拉选历史客户
    if not customer:
        customers_list = _get_customer_list()
        if customers_list:
            options = {
                f"{c.get('customer_name','未知')} · {c.get('customer_no','')} · {c.get('intent_level','')}意向": c
                for c in customers_list
            }
            selected_label = st.selectbox(
                "选择已录入的客户",
                ["— 请选择客户 —"] + list(options.keys()),
                key="sg_customer_select"
            )
            if selected_label != "— 请选择客户 —":
                customer = options[selected_label]
        else:
            st.info("💡 尚未录入任何客户，请先在「客户诊断」板块录入客户信息。")

    if customer:
        name     = customer.get("customer_name", "未知")
        no       = customer.get("customer_no", "-")
        intent   = customer.get("intent_level", "-")
        budget   = customer.get("budget_range", "-")
        stage    = customer.get("renovation_stage", "-")
        family   = customer.get("family_size", "-")
        special  = customer.get("special_needs", "无")
        focus    = "、".join(customer.get("focus_points") or []) or "-"
        card_ai  = customer.get("ai_card_result", "")
        intent_color = {"高": "#52c41a", "中": "#faad14", "低": "#ff4d4f"}.get(intent, "#999")

        with st.container():
            st.markdown(f"""
            <div style="background:#f8f9fa; border:1.5px solid #e0e0e0; border-radius:10px; padding:16px 20px;">
                <div style="display:flex; gap:32px; flex-wrap:wrap; margin-bottom:8px;">
                    <span><b>客户：</b>{name}</span>
                    <span><b>编号：</b>{no}</span>
                    <span><b>意向：</b><span style="color:{intent_color}; font-weight:bold;">{'⬤'} {intent}意向</span></span>
                    <span><b>预算：</b>{budget}</span>
                </div>
                <div style="display:flex; gap:32px; flex-wrap:wrap;">
                    <span><b>装修进度：</b>{stage}</span>
                    <span><b>家庭结构：</b>{family}</span>
                    <span><b>最在意：</b>{focus}</span>
                </div>
                <hr style="margin:10px 0; border-color:#e8e8e8;">
                <div>
                    <b>特殊需求：</b>{special}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 显示 A 模块 AI 核心结论（如果有）
        if card_ai:
            with st.expander("📌 A 模块核心结论（点击展开）", expanded=False):
                st.markdown(f"""
                <div style="white-space:pre-wrap; font-size:13px; color:#444; line-height:1.7;">
{card_ai[:500]}{"..." if len(card_ai) > 500 else ""}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("暂无客户数据，可直接填写下方设计要求进行方案分析")

    # ════════════════════════════════════════════════════════════════
    # ② 设计师修正栏（最高优先级）
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### ✏️ ② 设计师修正栏")

    col_hint, _ = st.columns([8, 1])
    with col_hint:
        with st.expander("？ 填写引导（点击查看示例）", expanded=False):
            st.markdown("""
**建议填写：**
- 客户现场补充的特殊需求、否决的方向、家人分歧点

**示例：**
> 太太坚持要白色哑光面；先生想保留不锈钢台面；取消餐边柜改西厨吧台

⚠️ **此栏优先级高于①自动传导的数据，如有冲突以本栏为准。**
""")

    designer_note = st.text_area(
        "设计师备注 / 调整要求",
        placeholder="例如：太太坚持要白色哑光面；先生想保留不锈钢台面；取消餐边柜改西厨搁板...",
        height=100,
        key="sg_designer_note"
    )

    # ════════════════════════════════════════════════════════════════
    # ③ 空间选择
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🏠 ③ 涉及空间（可多选）")
    st.caption("空间选择直接影响 AI 分析侧重点、选材建议和生图提示词的空间描述")

    space_cols = st.columns(len(SPACE_OPTIONS) + 1)
    selected_spaces = []
    for i, sp in enumerate(SPACE_OPTIONS):
        with space_cols[i]:
            if st.checkbox(sp, key=f"sg_space_{sp}"):
                selected_spaces.append(sp)

    with space_cols[-1]:
        custom_space = st.text_input("其他", placeholder="如：书房", key="sg_space_other")
    if custom_space.strip():
        selected_spaces.append(custom_space.strip())

    # ════════════════════════════════════════════════════════════════
    # ④ 风格 / 设计师参考
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🎨 ④ 风格 / 设计师参考")

    col_style, col_designer = st.columns([3, 2])
    with col_style:
        st.caption("参考风格方向（可多选）")
        selected_styles = st.multiselect(
            "参考风格",
            STYLE_OPTIONS,
            default=[],
            key="sg_styles",
            label_visibility="collapsed"
        )
        custom_style = st.text_input("其他风格（自填）", placeholder="如：有机现代、复古摩登", key="sg_custom_style")
        if custom_style.strip():
            selected_styles = selected_styles + [custom_style.strip()]

    with col_designer:
        st.caption("参考设计师（选填）")
        designer_ref = st.text_input(
            "参考设计师",
            placeholder="如：贝聿铭、深作吉、原研哉",
            key="sg_designer_ref",
            label_visibility="collapsed"
        )
        st.caption("大部分客户能说清风格偏好，但说不出设计师名字，选填即可")

    # ════════════════════════════════════════════════════════════════
    # ⑤ 品牌参考 + 预算对标
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🏷️ ⑤ 品牌参考 + 预算对标")

    col_brand_sel, col_brand_fill = st.columns([3, 2])
    with col_brand_sel:
        st.caption("客户提及的品牌 / 竞品（可多选）")
        selected_brands = st.multiselect(
            "品牌",
            BRAND_OPTIONS,
            default=[],
            key="sg_brands",
            label_visibility="collapsed"
        )
        custom_brand = st.text_input("其他品牌（自填）", placeholder="如：De Padova、方太", key="sg_custom_brand")
        if custom_brand.strip():
            selected_brands = selected_brands + [custom_brand.strip()]

    with col_brand_fill:
        st.caption("预算区间对标的参考品牌（AI 自动填充，可修改）")
        ai_brand_auto = _infer_budget_brands(customer.get("budget_range", "") if customer else "")
        ai_brand_fill = st.text_input(
            "预算对标品牌",
            value=ai_brand_auto,
            key="sg_ai_brand",
            label_visibility="collapsed"
        )

    # ════════════════════════════════════════════════════════════════
    # ⑥ 客户户型 & 现场照片
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📐 ⑥ 客户户型 & 现场照片")

    col_fp, col_photo = st.columns(2)

    with col_fp:
        st.markdown("**📐 户型平面图（必传 / 描述二选一）**")
        floor_plan_file = st.file_uploader(
            "上传户型图",
            type=["jpg", "jpeg", "png", "webp"],
            key="sg_floor_plan",
            label_visibility="collapsed"
        )
        if floor_plan_file:
            st.image(floor_plan_file, use_container_width=True, caption="户型图预览")

        has_desc = st.checkbox("仅知道大致房型（手动描述）", key="sg_floor_desc_toggle")
        floor_plan_desc = ""
        if has_desc:
            floor_plan_desc = st.text_area(
                "房型描述",
                placeholder="如：90㎡三室两厅，厨房约6㎡，L型，南向采光",
                height=80,
                key="sg_floor_desc"
            )
        elif floor_plan_file:
            floor_plan_desc = f"已上传户型图：{floor_plan_file.name}"

        st.markdown("**📏 关键尺寸备注（选填）**")
        key_dims = st.text_area(
            "关键尺寸",
            placeholder="如：灶台那面墙净宽2.4m，窗户下沿离地90cm，右侧有根排水管",
            height=70,
            key="sg_key_dims",
            label_visibility="collapsed"
        )

    with col_photo:
        st.markdown("**📸 现场照片（选传，最多 5 张）**")
        photo_files = st.file_uploader(
            "上传现场照片",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="sg_site_photos",
            label_visibility="collapsed"
        )
        if photo_files:
            photo_cols = st.columns(min(len(photo_files), 3))
            for i, f in enumerate(photo_files[:5]):
                with photo_cols[i % 3]:
                    st.image(f, use_container_width=True, caption=f.name)

        st.markdown("**照片类型标签（上传后标记）**")
        selected_photo_tags = []
        for tag in PHOTO_TAGS:
            if st.checkbox(tag, key=f"sg_phototag_{tag}"):
                selected_photo_tags.append(tag)

        photo_desc = st.text_input(
            "照片补充说明",
            placeholder="如：层高2.65m，右墙角有管道",
            key="sg_photo_desc"
        )

    # 户型图和照片的文字化描述（用于 Prompt）
    photo_info_for_prompt = ""
    if photo_files:
        photo_info_for_prompt = f"已上传 {len(photo_files[:5])} 张现场照片；标注类型：{', '.join(selected_photo_tags) or '未标注'}；补充说明：{photo_desc or '无'}"

    # ════════════════════════════════════════════════════════════════
    # ⑦ 参考图上传（最多2张）
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🖼️ ⑦ 参考图上传（最多 2 张）")
    st.caption("支持 JPG / PNG / WEBP · 单边 ≤ 1680px · 大小 ≤ 2MB | AI 必须在风格建议和生图提示词中引用其核心元素")

    ref_files = st.file_uploader(
        "上传参考图",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="sg_ref_images"
    )
    if ref_files:
        ref_cols = st.columns(min(len(ref_files), 2))
        for i, f in enumerate(ref_files[:2]):
            with ref_cols[i]:
                st.image(f, use_container_width=True, caption=f.name)

    ref_images_desc = ""
    if ref_files:
        ref_images_desc = f"已上传 {min(len(ref_files), 2)} 张参考图（{', '.join(f.name for f in ref_files[:2])}）。请在风格方向板块引用参考图中的核心视觉元素（布局、配色、特殊设计），并在生图提示词中融入。"

    # ════════════════════════════════════════════════════════════════
    # ⑧ AI 设计分析
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🤖 ⑧ AI 设计分析")

    col_gen, col_reset = st.columns([3, 1])
    with col_gen:
        gen_btn = st.button(
            "🤖 生成 AI 设计方案分析（7 板块）",
            type="primary",
            use_container_width=True,
            key="sg_gen_analysis"
        )
    with col_reset:
        if st.button("🔄 清空结果", use_container_width=True, key="sg_clear"):
            st.session_state.sg_analysis_result = ""
            st.session_state.sg_generated_image = None
            st.rerun()

    if gen_btn:
        with st.spinner("🤖 正在生成设计方案分析（7 板块 + 生图提示词，约 20~40 秒）..."):
            try:
                from core.ai_service import get_ai_service
                ai = get_ai_service()

                full_prompt = _build_design_analysis_prompt(
                    customer=customer or {},
                    designer_note=designer_note,
                    selected_spaces=selected_spaces,
                    selected_styles=selected_styles,
                    designer_ref=designer_ref if "designer_ref" in dir() else "",
                    selected_brands=selected_brands,
                    ai_brand_fill=ai_brand_fill if "ai_brand_fill" in dir() else "",
                    floor_plan_desc=floor_plan_desc if "floor_plan_desc" in dir() else "",
                    key_dims=key_dims if "key_dims" in dir() else "",
                    photo_tags=selected_photo_tags if "selected_photo_tags" in dir() else [],
                    photo_desc=photo_desc if "photo_desc" in dir() else "",
                    ref_images_desc=ref_images_desc,
                )

                resp = ai.client.chat.completions.create(
                    model=ai.model,
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.65,
                    max_tokens=3500
                )
                result = resp.choices[0].message.content.strip()
                st.session_state.sg_analysis_result = result
                st.rerun()
            except Exception as e:
                st.error(f"❌ AI 分析失败：{str(e)}")

    # ── 展示 AI 分析结果 ──────────────────────────────────────────
    analysis_result = st.session_state.get("sg_analysis_result", "")
    if analysis_result:
        st.markdown("""
        <div style="background:#e6f4ff; border:1.5px solid #91caff; border-radius:8px;
                    padding:6px 14px; margin:12px 0 4px 0;">
            <strong>🎨 AI 设计方案分析结果（7 板块）</strong>
        </div>
        """, unsafe_allow_html=True)

        # 渲染分析内容
        st.markdown(f"""
        <div style="background:#f6fbff; border:1px solid #bae0ff; border-radius:8px;
                    padding:18px 20px; white-space:pre-wrap; font-size:14px; line-height:2;
                    font-family:'PingFang SC','Microsoft YaHei',sans-serif;">
{analysis_result}
        </div>
        """, unsafe_allow_html=True)

        # 一键复制
        st.markdown("<br>", unsafe_allow_html=True)
        st.code(analysis_result, language=None)
        st.caption("💡 点击上方代码框右上角的复制图标，即可一键复制全部分析结果")

        # ── 生图按钮（从分析结果里提取 Prompt 1 的关键词） ────────
        st.markdown("---")
        st.markdown("#### 🖼️ AI 生成效果图")
        st.caption("系统将使用上方分析结果中的 Prompt 1 主空间全景生图")

        col_img1, col_img2 = st.columns([3, 1])
        with col_img1:
            custom_img_prompt = st.text_area(
                "自定义生图 Prompt（英文，留空则使用 AI 分析中的 Prompt 1）",
                height=90,
                key="sg_custom_img_prompt",
                placeholder="Positive prompt (English) — leave blank to auto-extract from analysis"
            )
        with col_img2:
            st.markdown("<br>", unsafe_allow_html=True)
            gen_img_btn = st.button("🎨 生成效果图", type="secondary",
                                    use_container_width=True, key="sg_gen_image")

        if gen_img_btn:
            # 提取 Prompt 1
            image_prompt = custom_img_prompt.strip()
            if not image_prompt:
                # 自动从分析结果中提取 Prompt 1 Positive
                lines = analysis_result.split("\n")
                in_prompt1 = False
                for i, line in enumerate(lines):
                    if "Prompt 1" in line or "主空间全景" in line:
                        in_prompt1 = True
                    if in_prompt1 and "[EN] Positive" in line:
                        # 收集接下来的非空行直到遇到 Negative 或下一个 Prompt
                        extracted = []
                        for j in range(i + 1, min(i + 8, len(lines))):
                            l = lines[j].strip()
                            if l.startswith("[EN] Negative") or l.startswith("[CN") or l.startswith("━"):
                                break
                            if l:
                                extracted.append(l)
                        image_prompt = " ".join(extracted)
                        break

            if not image_prompt:
                # 最后的 fallback
                image_prompt = (
                    f"modern minimalist custom stainless steel kitchen, "
                    f"{''.join(selected_styles[:2]) or 'minimalist'} style, "
                    f"photorealistic interior design, 8k, --ar 16:9"
                )

            with st.spinner("🎨 正在生成效果图（约 30~60 秒）..."):
                try:
                    from core.config import config
                    img_bytes = _generate_image(
                        prompt=image_prompt,
                        api_key=config.ai.api_key,
                        base_url=config.ai.base_url,
                        model="dall-e-3"
                    )
                    st.session_state.sg_generated_image = img_bytes
                    st.session_state.sg_image_prompt = image_prompt
                    st.rerun()
                except Exception as e:
                    st.warning(f"⚠️ 生图接口暂不可用（{str(e)[:80]}）")
                    st.info("""
💡 **生图降级方案**：当前 API 不支持图像生成接口。

你可以复制下方提示词，到以下平台手动生成：
- [Midjourney](https://www.midjourney.com/)
- [即梦 AI](https://jimeng.jianying.com/)
- [可灵 AI](https://klingai.kuaishou.com/)
                    """)
                    st.markdown("**📋 Prompt 1 主空间全景（可直接复制使用）：**")
                    st.code(image_prompt, language=None)

    # ── 展示已生成的效果图 ────────────────────────────────────────
    if st.session_state.get("sg_generated_image"):
        st.markdown("---")
        st.image(st.session_state.sg_generated_image, use_container_width=True,
                 caption="AI 生成效果图（主空间全景）")
        st.caption(f"生图 Prompt：{st.session_state.get('sg_image_prompt', '')[:200]}")

        col_dl, col_regen = st.columns(2)
        with col_dl:
            st.download_button(
                label="⬇️ 下载效果图",
                data=st.session_state.sg_generated_image,
                file_name="design_preview.png",
                mime="image/png",
                use_container_width=True
            )
        with col_regen:
            if st.button("🔄 重新生成", use_container_width=True, key="sg_regen_image"):
                st.session_state.sg_generated_image = None
                st.session_state.sg_image_prompt = ""
                st.rerun()
