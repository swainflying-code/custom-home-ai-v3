"""
成交魔方 V3 — 预算锚定（C 模块）
规格：pricing-engine-c-spec.md v1.0

核心原则：AI 只负责「拆解」，所有价格数字从后台 pricing_engine 读取，AI 永远不碰价格。
数据流：A 客户诊断 → B 方案引导 → C 预算锚定（本模块）
"""

import streamlit as st
import json
import traceback

from core.pricing_engine import (
    CATEGORY_META, TIER_LABELS, BUDGET_RANGE_MAP,
    load_table, calculate, add_install, budget_check,
    recommend_categories, format_price_range, get_tier_key
)

# ───────────────────────────────────────────────────────────────
# 常量
# ───────────────────────────────────────────────────────────────

COUNTERTOP_OPTIONS = {
    "304 拉丝不锈钢":      "304_brushed",
    "304 防指纹不锈钢":    "304_antiFingerprint",
    "石英石":              "quartz",
    "不锈钢+石英石拼接":   "mixed_steel_quartz",
}

FLOOR_OPTIONS = {"有电梯": "elevator", "无电梯（5层+）": "no_elevator", "远郊/跨区": "remote"}
DEMO_OPTIONS  = {"不需要拆旧": 0, "少量拆旧 ¥500": 500, "大量拆旧 ¥1500": 1500, "全屋拆旧 ¥2000": 2000}

# ── KC 模块列表（代码→名称+档位价格供显示） ──
KC_MODULES = []
try:
    _kc = load_table("KC")
    KC_MODULES = _kc.get("modules", [])
except Exception:
    pass


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def show_budget_anchor_page():
    # ── 页头 ──────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:16px 0 4px;">
        <h2 style="margin:0; color:#1a1a1a;">💰 预算锚定</h2>
        <p style="margin:4px 0 0; color:#666; font-size:14px;">
            承接客户诊断 & 方案引导的数据 · 五分钟出三档精准报价 · 精度 ±10%
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 初始化报价 session ─────────────────────────────────────
    if "quotes" not in st.session_state:
        st.session_state.quotes = {}          # {category_code: {tier: result}}
    if "selected_categories" not in st.session_state:
        st.session_state.selected_categories = []
    if "quote_customer" not in st.session_state:
        st.session_state.quote_customer = None

    # ── 四个 Tab ───────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "① 选择客户 & 品类",
        "② 填写报价参数",
        "③ 多品类汇总",
        "④ 报价单导出",
    ])

    with tab1:
        _tab_customer_and_category()
    with tab2:
        _tab_fill_params()
    with tab3:
        _tab_summary()
    with tab4:
        _tab_export()


# ═══════════════════════════════════════════════════════════════
# Tab 1 — 选择客户 & 品类
# ═══════════════════════════════════════════════════════════════

def _tab_customer_and_category():
    st.markdown("### 📡 承接客户数据")

    # ── 选择客户 ──────────────────────────────────────────────
    customers = _get_customers()
    if customers:
        options = {f"{c.get('customer_no','—')} · {c.get('customer_name','—')} · {c.get('budget_range','未知')} · {c.get('intent_level','—')}意向": c
                   for c in customers}
        sel = st.selectbox("选择客户", ["— 请选择 —"] + list(options.keys()), key="c_sel")
        if sel != "— 请选择 —":
            customer = options[sel]
            st.session_state.quote_customer = customer
            # 自动推荐品类
            spaces = customer.get("custom_spaces") or []
            recommended = recommend_categories(spaces)
            if recommended and not st.session_state.selected_categories:
                st.session_state.selected_categories = recommended
    else:
        st.info("暂无客户记录，可手动填写客户信息继续报价")

    # ── 显示客户摘要 ───────────────────────────────────────────
    customer = st.session_state.get("quote_customer")
    if customer:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("客户", customer.get("customer_name", "—"))
        col2.metric("预算", customer.get("budget_range", "未知"))
        intent = customer.get("intent_level", "—")
        col3.metric("意向", f"{'🟢' if intent == '高' else '🟡' if intent == '中' else '🔴'} {intent}")
        spaces_str = "、".join(customer.get("custom_spaces") or []) or "未指定"
        col4.metric("涉及空间", spaces_str[:10] + ("…" if len(spaces_str) > 10 else ""))

    # ── 手动填入（无客户时） ───────────────────────────────────
    if not customer:
        with st.expander("手动填入客户基本信息"):
            c1, c2, c3 = st.columns(3)
            name   = c1.text_input("客户姓名", key="manual_name")
            budget = c2.selectbox("预算区间", list(BUDGET_RANGE_MAP.keys()), key="manual_budget")
            intent = c3.selectbox("意向等级", ["高", "中", "低"], key="manual_intent")
            if name:
                st.session_state.quote_customer = {
                    "customer_name": name,
                    "budget_range":  budget,
                    "intent_level":  intent,
                    "custom_spaces": [],
                }

    st.markdown("---")
    st.markdown("### 🗂️ 选择报价品类（可多选）")

    # ── 品类按钮网格 ───────────────────────────────────────────
    _category_grid()

    # ── 推荐提示 ───────────────────────────────────────────────
    customer = st.session_state.get("quote_customer")
    spaces = (customer or {}).get("custom_spaces") or []
    if spaces:
        recommended = recommend_categories(spaces)
        if recommended:
            rec_names = "、".join(CATEGORY_META[c]["name"] for c in recommended if c in CATEGORY_META)
            st.info(f"💡 根据 B 模块空间选择「{'、'.join(spaces)}」推荐报价品类：**{rec_names}**")

    sel = st.session_state.selected_categories
    if sel:
        names = "、".join(f"{CATEGORY_META[c]['emoji']}{CATEGORY_META[c]['name']}" for c in sel if c in CATEGORY_META)
        st.success(f"已选 {len(sel)} 个品类：{names}　→ 前往 **② 填写报价参数**")


def _category_grid():
    codes = list(CATEGORY_META.keys())
    cols = st.columns(5)
    for i, code in enumerate(codes):
        meta = CATEGORY_META[code]
        selected = code in st.session_state.selected_categories
        label = f"{'✅ ' if selected else ''}{meta['emoji']} {meta['name']}"
        if cols[i % 5].button(label, key=f"cat_btn_{code}", use_container_width=True):
            if selected:
                st.session_state.selected_categories.remove(code)
            else:
                st.session_state.selected_categories.append(code)
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# Tab 2 — 填写报价参数
# ═══════════════════════════════════════════════════════════════

def _tab_fill_params():
    sel = st.session_state.get("selected_categories", [])
    if not sel:
        st.info("请先在 **① 选择客户 & 品类** 中勾选要报价的品类")
        return

    customer = st.session_state.get("quote_customer") or {}

    for code in sel:
        meta = CATEGORY_META[code]
        st.markdown(f"---\n### {meta['emoji']} {meta['name']}（{meta['unit']}）")

        with st.container():
            tier = st.radio(
                "档位", TIER_LABELS,
                horizontal=True,
                index=1,
                key=f"tier_{code}",
            )

            if code == "KC":
                _fill_kc(code, tier, customer)
            elif code == "WD":
                _fill_wd(code, tier, customer)
            elif code in ("YG", "JZ", "CB", "TG"):
                _fill_linear(code, tier, customer)
            elif code == "XG":
                _fill_unit(code, tier, customer)
            elif code in ("SN", "SH", "JIU"):
                _fill_area(code, tier, customer)


# ─── KC 橱柜 ────────────────────────────────────────────────────
def _fill_kc(code, tier, customer):
    t = load_table("KC")
    tk = get_tier_key(tier)

    c1, c2, c3 = st.columns(3)
    base_m = c1.number_input("地柜延米（m）",   min_value=0.0, value=3.0, step=0.1, key=f"{code}_base")
    wall_m = c2.number_input("吊柜延米（m）",   min_value=0.0, value=2.0, step=0.1, key=f"{code}_wall")
    ct_m   = c3.number_input("台面延米（m）",   min_value=0.0, value=base_m, step=0.1, key=f"{code}_ct")

    ct_type_label = st.selectbox("台面材质", list(COUNTERTOP_OPTIONS.keys()), index=1, key=f"{code}_ct_type")
    ct_type = COUNTERTOP_OPTIONS[ct_type_label]
    ct_depth = st.radio("台面深度", ["标准(600mm)", "加深(650mm+)", "瀑布边"], horizontal=True, key=f"{code}_depth")
    depth_map = {"标准(600mm)": "standard", "加深(650mm+)": "deep", "瀑布边": "waterfall"}

    # 模块清单
    st.markdown("**模块清单**（可参考 B 模块 AI 输出，手动调整）")
    modules = []
    mod_names = [f"{m['code']} {m['name']}" for m in t["modules"]]
    num_modules = st.number_input("模块行数", min_value=0, max_value=20, value=3, key=f"{code}_mod_rows")

    for i in range(int(num_modules)):
        mc1, mc2, mc3 = st.columns([3, 1, 2])
        mod_sel = mc1.selectbox(f"模块{i+1}", mod_names, key=f"{code}_mod_{i}")
        qty     = mc2.number_input("数量", min_value=0, max_value=50, value=1, key=f"{code}_qty_{i}")
        mod_code = mod_sel.split(" ")[0]
        mod_obj  = next((m for m in t["modules"] if m["code"] == mod_code), None)
        if mod_obj:
            unit_price = mod_obj.get(tk, 0)
            mc3.markdown(f"<small>单价 ¥{unit_price:,} · 小计 ¥{unit_price * qty:,}</small>", unsafe_allow_html=True)
            if qty > 0:
                modules.append({"code": mod_code, "qty": qty})

    # 安装
    c4, c5 = st.columns(2)
    floor_lbl = c4.selectbox("楼层情况", list(FLOOR_OPTIONS.keys()), key=f"{code}_floor")
    demo_lbl  = c5.selectbox("拆旧", list(DEMO_OPTIONS.keys()), key=f"{code}_demo")

    params = {
        "base_meters": base_m, "wall_meters": wall_m,
        "countertop_meters": ct_m, "countertop_type": ct_type,
        "countertop_depth": depth_map[ct_depth],
        "modules": modules,
    }

    if st.button(f"🧮 计算 橱柜", key=f"calc_{code}", type="primary"):
        result = calculate(code, params, tier)
        result = add_install(result, "linear", base_m, "urban", FLOOR_OPTIONS[floor_lbl])
        result["breakdown"]["拆旧"] = DEMO_OPTIONS[demo_lbl]
        result["total"] += DEMO_OPTIONS[demo_lbl]
        if code not in st.session_state.quotes:
            st.session_state.quotes[code] = {}
        st.session_state.quotes[code][tier] = result

    _show_result(code, tier)


# ─── WD 衣柜 ────────────────────────────────────────────────────
def _fill_wd(code, tier, customer):
    t = load_table("WD")
    tk = get_tier_key(tier)

    c1, c2 = st.columns(2)
    width  = c1.number_input("柜体宽度（m）",  min_value=0.0, value=1.8, step=0.1, key=f"{code}_w")
    height = c2.number_input("柜体高度（m）",  min_value=0.0, value=2.4, step=0.1, key=f"{code}_h")
    sqm = width * height
    st.caption(f"投影面积：{sqm:.2f} ㎡")

    door_labels = list(t["doorUpgrades"].keys())
    door_label_map = {k: t["doorUpgrades"][k]["name"] for k in door_labels}
    door_type = st.selectbox("门板类型", door_labels,
                             format_func=lambda k: door_label_map[k],
                             key=f"{code}_door")
    door_qty = st.number_input("门板扇数（玻璃/镜面/皮革时填）", min_value=0, value=2, key=f"{code}_dq")

    def _pkg_suffix(v):
        return " (含基准价)" if v["price"] == 0 else f" (+¥{v['price']:,}/组)"
    pkg_labels = {k: f"{v['name']} — {v['desc']}{_pkg_suffix(v)}"
                  for k, v in t["interiorPackages"].items()}
    pkg = st.selectbox("内部配置包", list(pkg_labels.keys()), format_func=lambda k: pkg_labels[k], key=f"{code}_pkg")

    c3, c4 = st.columns(2)
    floor_lbl = c3.selectbox("楼层情况", list(FLOOR_OPTIONS.keys()), key=f"{code}_floor")
    demo_lbl  = c4.selectbox("拆旧", list(DEMO_OPTIONS.keys()), key=f"{code}_demo")

    params = {"width": width, "height": height,
              "door_type": door_type, "interior_pkg": pkg, "door_qty": door_qty}

    if st.button(f"🧮 计算 衣柜", key=f"calc_{code}", type="primary"):
        result = calculate(code, params, tier)
        result = add_install(result, "area", sqm, "urban", FLOOR_OPTIONS[floor_lbl])
        result["breakdown"]["拆旧"] = DEMO_OPTIONS[demo_lbl]
        result["total"] += DEMO_OPTIONS[demo_lbl]
        if code not in st.session_state.quotes:
            st.session_state.quotes[code] = {}
        st.session_state.quotes[code][tier] = result

    _show_result(code, tier)


# ─── 延米品类（YG/JZ/CB/TG） ────────────────────────────────────
def _fill_linear(code, tier, customer):
    t    = load_table(code)
    tk   = get_tier_key(tier)
    meta = CATEGORY_META[code]

    meters = st.number_input(f"{meta['name']} 延米（m）", min_value=0.0, value=2.0, step=0.1, key=f"{code}_m")

    sub_options = list(t["tiers"][tk].keys())
    sub_labels  = {k: f"{k.replace('_perMeter', '').replace('_', ' ')} · ¥{t['tiers'][tk][k]:,}/延米"
                   for k in sub_options}
    sub_type = st.selectbox("类型", sub_options, format_func=lambda k: sub_labels[k], key=f"{code}_sub")

    # 配件
    acc_cfg = t.get("accessories", {})
    accessories = []
    if acc_cfg:
        st.markdown("**特有配件**")
        for akey, aval in acc_cfg.items():
            if isinstance(aval, dict):
                price_str = f"¥{aval.get('min',0):,}~¥{aval.get('max',0):,}"
            else:
                price_str = f"¥{aval:,}"
            checked = st.checkbox(f"{akey.replace('_', ' ')}  {price_str}", key=f"{code}_acc_{akey}")
            if checked:
                qty = st.number_input("数量", min_value=1, value=1, key=f"{code}_acc_qty_{akey}")
                accessories.append({"key": akey, "qty": qty})

    c1, c2 = st.columns(2)
    floor_lbl = c1.selectbox("楼层情况", list(FLOOR_OPTIONS.keys()), key=f"{code}_floor")
    demo_lbl  = c2.selectbox("拆旧", list(DEMO_OPTIONS.keys()), key=f"{code}_demo")

    params = {"meters": meters, "sub_type": sub_type, "accessories": accessories}

    if st.button(f"🧮 计算 {meta['name']}", key=f"calc_{code}", type="primary"):
        result = calculate(code, params, tier)
        result = add_install(result, "linear", meters, "urban", FLOOR_OPTIONS[floor_lbl])
        result["breakdown"]["拆旧"] = DEMO_OPTIONS[demo_lbl]
        result["total"] += DEMO_OPTIONS[demo_lbl]
        if code not in st.session_state.quotes:
            st.session_state.quotes[code] = {}
        st.session_state.quotes[code][tier] = result

    _show_result(code, tier)


# ─── 单组品类（XG） ─────────────────────────────────────────────
def _fill_unit(code, tier, customer):
    t    = load_table(code)
    tk   = get_tier_key(tier)
    meta = CATEGORY_META[code]

    qty = st.number_input(f"{meta['name']} 数量（组）", min_value=1, value=1, key=f"{code}_qty")

    sub_options = list(t["tiers"][tk].keys())
    sub_labels  = {k: f"{k.replace('_perUnit', '').replace('_', ' ')} · ¥{t['tiers'][tk][k]:,}/组"
                   for k in sub_options}
    sub_type = st.selectbox("类型", sub_options, format_func=lambda k: sub_labels[k], key=f"{code}_sub")

    acc_cfg = t.get("accessories", {})
    accessories = []
    if acc_cfg:
        st.markdown("**特有配件**")
        for akey, aval in acc_cfg.items():
            if isinstance(aval, dict):
                price_str = f"¥{aval.get('min',0):,}~¥{aval.get('max',0):,}"
            else:
                price_str = f"¥{aval:,}"
            checked = st.checkbox(f"{akey.replace('_', ' ')}  {price_str}", key=f"{code}_acc_{akey}")
            if checked:
                qty_a = st.number_input("数量", min_value=1, value=1, key=f"{code}_acc_qty_{akey}")
                accessories.append({"key": akey, "qty": qty_a})

    c1, c2 = st.columns(2)
    floor_lbl = c1.selectbox("楼层情况", list(FLOOR_OPTIONS.keys()), key=f"{code}_floor")
    demo_lbl  = c2.selectbox("拆旧", list(DEMO_OPTIONS.keys()), key=f"{code}_demo")

    params = {"qty": qty, "sub_type": sub_type, "accessories": accessories}

    if st.button(f"🧮 计算 {meta['name']}", key=f"calc_{code}", type="primary"):
        result = calculate(code, params, tier)
        result = add_install(result, "unit", qty, "urban", FLOOR_OPTIONS[floor_lbl])
        result["breakdown"]["拆旧"] = DEMO_OPTIONS[demo_lbl]
        result["total"] += DEMO_OPTIONS[demo_lbl]
        if code not in st.session_state.quotes:
            st.session_state.quotes[code] = {}
        st.session_state.quotes[code][tier] = result

    _show_result(code, tier)


# ─── 投影面积品类（SN/SH/JIU） ──────────────────────────────────
def _fill_area(code, tier, customer):
    t    = load_table(code)
    tk   = get_tier_key(tier)
    meta = CATEGORY_META[code]

    c1, c2 = st.columns(2)
    width  = c1.number_input(f"宽（m）", min_value=0.0, value=1.2, step=0.1, key=f"{code}_w")
    height = c2.number_input(f"高（m）", min_value=0.0, value=2.0, step=0.1, key=f"{code}_h")
    sqm = width * height
    st.caption(f"投影面积：{sqm:.2f} ㎡")

    sub_options = list(t["tiers"][tk].keys())
    sub_labels  = {k: f"{k.replace('_perSqm', '').replace('_', ' ')} · ¥{t['tiers'][tk][k]:,}/㎡"
                   for k in sub_options}
    sub_type = st.selectbox("类型", sub_options, format_func=lambda k: sub_labels[k], key=f"{code}_sub")

    acc_cfg = t.get("accessories", {})
    accessories = []
    if acc_cfg:
        st.markdown("**特有配件**")
        for akey, aval in acc_cfg.items():
            if isinstance(aval, dict):
                price_str = f"¥{aval.get('min',0):,}~¥{aval.get('max',0):,}"
            else:
                price_str = f"¥{aval:,}"
            checked = st.checkbox(f"{akey.replace('_', ' ')}  {price_str}", key=f"{code}_acc_{akey}")
            if checked:
                qty_a = st.number_input("数量", min_value=1, value=1, key=f"{code}_acc_qty_{akey}")
                accessories.append({"key": akey, "qty": qty_a})

    c3, c4 = st.columns(2)
    floor_lbl = c3.selectbox("楼层情况", list(FLOOR_OPTIONS.keys()), key=f"{code}_floor")
    demo_lbl  = c4.selectbox("拆旧", list(DEMO_OPTIONS.keys()), key=f"{code}_demo")

    params = {"width": width, "height": height, "sub_type": sub_type, "accessories": accessories}

    if st.button(f"🧮 计算 {meta['name']}", key=f"calc_{code}", type="primary"):
        result = calculate(code, params, tier)
        result = add_install(result, "area", sqm, "urban", FLOOR_OPTIONS[floor_lbl])
        result["breakdown"]["拆旧"] = DEMO_OPTIONS[demo_lbl]
        result["total"] += DEMO_OPTIONS[demo_lbl]
        if code not in st.session_state.quotes:
            st.session_state.quotes[code] = {}
        st.session_state.quotes[code][tier] = result

    _show_result(code, tier)


# ─── 单品类结果展示 ──────────────────────────────────────────────
def _show_result(code, tier):
    result = (st.session_state.quotes.get(code) or {}).get(tier)
    if not result:
        return
    total = result["total"]
    st.markdown(f"""
    <div style="background:#f0f8f0;border-left:4px solid #2ecc71;border-radius:8px;padding:14px 18px;margin:12px 0;">
        <div style="font-size:20px;font-weight:800;color:#1a1a1a;">
            💰 {CATEGORY_META[code]['name']} · {tier} 小计：¥{total:,.0f}
        </div>
        <div style="font-size:12px;color:#666;margin-top:4px;">
            精度范围：{format_price_range(total)}（±10%）
        </div>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("查看明细"):
        for k, v in result["breakdown"].items():
            st.markdown(f"- **{k}**：¥{v:,.0f}")


# ═══════════════════════════════════════════════════════════════
# Tab 3 — 多品类汇总
# ═══════════════════════════════════════════════════════════════

def _tab_summary():
    customer = st.session_state.get("quote_customer") or {}
    quotes   = st.session_state.get("quotes", {})
    sel      = st.session_state.get("selected_categories", [])

    if not sel:
        st.info("请先在 **①** 选择品类，在 **②** 填写并计算报价")
        return

    name   = customer.get("customer_name", "未知客户")
    budget = customer.get("budget_range", "未透露")
    intent = customer.get("intent_level", "—")

    st.markdown(f"### 📊 方案总报价 &nbsp; 客户：{name} | 预算：{budget} | 意向：{intent}")

    # ── 档位选择器（全局） ─────────────────────────────────────
    global_tier = st.radio("统一档位查看", TIER_LABELS, horizontal=True, index=1, key="summary_tier")

    rows = []
    total_sum = 0

    for code in sel:
        meta = CATEGORY_META[code]
        tier_quotes = quotes.get(code, {})
        result = tier_quotes.get(global_tier)

        if result:
            rows.append({
                "品类": f"{meta['emoji']} {meta['name']}",
                "档位": global_tier,
                "小计（元）": result["total"],
                "状态": "✅ 已报",
            })
            total_sum += result["total"]
        else:
            rows.append({
                "品类": f"{meta['emoji']} {meta['name']}",
                "档位": global_tier,
                "小计（元）": "—",
                "状态": "⏳ 待报",
            })

    # ── 明细表格 ───────────────────────────────────────────────
    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── 合计 & 预算校验 ────────────────────────────────────────
    if total_sum > 0:
        check = budget_check(total_sum, budget)
        status_color = "#2ecc71" if check["status"] == "ok" else "#e74c3c" if check["status"] == "over" else "#3498db"

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:20px 24px;margin:16px 0;">
            <div style="font-size:26px;font-weight:900;color:#1a1a1a;">
                💰 已报价合计：¥{total_sum:,.0f}
            </div>
            <div style="font-size:13px;margin-top:6px;color:{status_color};font-weight:600;">
                {check['msg']}
            </div>
            <div style="font-size:12px;color:#999;margin-top:4px;">
                精度范围：{format_price_range(total_sum)}（±10%）
            </div>
        </div>
        """, unsafe_allow_html=True)

        if check["suggestions"]:
            st.markdown("**💡 AI 降价建议：**")
            for s in check["suggestions"]:
                st.markdown(f"- {s}")

    # ── 三档对比表 ─────────────────────────────────────────────
    st.markdown("---\n### 三档对比")
    tier_totals = {"经济款": 0, "品质款": 0, "旗舰款": 0}
    all_have = True
    for code in sel:
        for t_label in TIER_LABELS:
            r = (quotes.get(code) or {}).get(t_label)
            if r:
                tier_totals[t_label] += r["total"]
            else:
                all_have = False

    if all_have or any(v > 0 for v in tier_totals.values()):
        ct1, ct2, ct3 = st.columns(3)
        for col, t_label, color in zip([ct1, ct2, ct3], TIER_LABELS, ["#95a5a6", "#3498db", "#e67e22"]):
            v = tier_totals[t_label]
            if v > 0:
                col.markdown(f"""
                <div style="background:{color};color:white;border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:14px;font-weight:600;">{t_label}</div>
                    <div style="font-size:22px;font-weight:900;">¥{v:,.0f}</div>
                    <div style="font-size:11px;opacity:.8;">{format_price_range(v)}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("请先在 **②** 对各档位分别计算，三档对比才能显示")


# ═══════════════════════════════════════════════════════════════
# Tab 4 — 报价单导出
# ═══════════════════════════════════════════════════════════════

def _tab_export():
    customer = st.session_state.get("quote_customer") or {}
    quotes   = st.session_state.get("quotes", {})
    sel      = st.session_state.get("selected_categories", [])

    if not quotes:
        st.info("请先完成报价计算，再导出报价单")
        return

    name   = customer.get("customer_name", "未知客户")
    budget = customer.get("budget_range", "未透露")
    tier   = st.selectbox("导出档位", TIER_LABELS, index=1, key="export_tier")

    lines = []
    lines.append(f"# 方案报价单（L2 精度：±10%）")
    lines.append(f"客户：{name} | 预算：{budget} | 档位：{tier}")
    lines.append(f"日期：2026-03-30\n")

    total_sum = 0
    for code in sel:
        meta = CATEGORY_META[code]
        result = (quotes.get(code) or {}).get(tier)
        if result:
            lines.append(f"## {meta['emoji']} {meta['name']}")
            for k, v in result["breakdown"].items():
                lines.append(f"  · {k}：¥{v:,.0f}")
            lines.append(f"  **小计：¥{result['total']:,.0f}**\n")
            total_sum += result["total"]

    if total_sum:
        lines.append("---")
        lines.append(f"## 💰 合计：¥{total_sum:,.0f}")
        lines.append(f"精度范围：{format_price_range(total_sum)}（±10%）")
        chk = budget_check(total_sum, budget)
        lines.append(chk["msg"])
        lines.append("\n⚠️ 本报价基于初步方案（L2精度），最终以确认图纸后的 L3 报价为准")

    report_text = "\n".join(lines)
    st.text_area("报价单预览", report_text, height=400, key="report_preview")

    # ── 复制按钮 ───────────────────────────────────────────────
    st.components.v1.html(f"""
    <button onclick="
        navigator.clipboard.writeText({json.dumps(report_text)}).then(()=>{{
            this.innerText='✅ 已复制！';
            setTimeout(()=>this.innerText='📋 一键复制报价单', 2000);
        }});
    " style="
        background:#c9a84c;color:white;border:none;border-radius:8px;
        padding:10px 24px;font-size:15px;cursor:pointer;font-weight:600;
    ">📋 一键复制报价单</button>
    """, height=50)

    # ── 保存到数据库 ───────────────────────────────────────────
    if st.button("💾 保存报价记录到数据库", key="save_quote"):
        _save_quote(customer, quotes, tier, total_sum, report_text)


def _save_quote(customer, quotes, tier, total, text):
    try:
        from core.database import db
        cid = customer.get("id")
        payload = {
            "customer_id":   cid,
            "customer_name": customer.get("customer_name", ""),
            "budget_range":  customer.get("budget_range", ""),
            "tier":          tier,
            "total_amount":  total,
            "quote_detail":  json.dumps(quotes, ensure_ascii=False),
            "report_text":   text,
        }
        db.client.table("quotes_v3").insert(payload).execute()
        st.success("✅ 报价记录已保存")
    except Exception as e:
        st.warning(f"保存失败（数据库未就绪时可忽略）：{e}")


# ═══════════════════════════════════════════════════════════════
# 工具
# ═══════════════════════════════════════════════════════════════

def _get_customers():
    try:
        from core.database import db
        return db.select("customers_v3", order_by="created_at.desc", limit=100) or []
    except Exception:
        return []
