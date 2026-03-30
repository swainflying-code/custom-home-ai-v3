"""
成交魔方 V3 — 价格后台管理
仅 admin 角色可访问。
功能：
  · 查看 & 修改各品类基准价
  · 查看 & 修改通用安装/工艺价格
  · 价格变更日志（session 内记录）
  · 修改后立即生效（写入 pricing/*.json）
"""

import streamlit as st
import json
import copy
from datetime import datetime

from core.pricing_engine import (
    CATEGORY_META, TIER_LABELS,
    load_table, save_table,
    load_common, save_common,
)

CHANGE_LOG_KEY = "_admin_price_change_log"


# ═══════════════════════════════════════════════════════════════
# 权限检查
# ═══════════════════════════════════════════════════════════════

def show_admin_pricing_page():
    user = st.session_state.get("user_info") or {}
    role = user.get("role", "")
    if role != "admin":
        st.error("🔒 此页面仅限管理员访问")
        st.info("请使用 admin 账号登录后访问")
        return

    st.markdown("""
    <div style="padding:16px 0 4px;">
        <h2 style="margin:0; color:#1a1a1a;">🔧 价格后台管理</h2>
        <p style="margin:4px 0 0; color:#666; font-size:14px;">
            修改基准价表 · 立即生效 · 变更有日志 · 仅管理员可见
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_names = ["品类基准价"] + ["通用安装/工艺"] + ["变更日志"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _tab_category_prices()
    with tabs[1]:
        _tab_common_prices()
    with tabs[2]:
        _tab_change_log()


# ═══════════════════════════════════════════════════════════════
# Tab 1 — 品类基准价
# ═══════════════════════════════════════════════════════════════

def _tab_category_prices():
    code = st.selectbox(
        "选择品类",
        list(CATEGORY_META.keys()),
        format_func=lambda k: f"{CATEGORY_META[k]['emoji']} {CATEGORY_META[k]['name']} ({k})",
        key="admin_cat_sel",
    )
    meta = CATEGORY_META[code]
    st.markdown(f"#### {meta['emoji']} {meta['name']} — 计价单位：{meta['unit']}")

    try:
        data = load_table(code)
    except Exception as e:
        st.error(f"读取价格表失败：{e}")
        return

    old_data = copy.deepcopy(data)

    # ── 档位基准价 ────────────────────────────────────────────
    st.markdown("**档位基准价**")
    tiers = data.get("tiers", {})
    tier_keys = list(tiers.get("economy", {}).keys()) if tiers else []

    changed = False

    for tier_label, tier_code in [("经济款", "economy"), ("品质款", "quality"), ("旗舰款", "flagship")]:
        if tier_code not in tiers:
            continue
        st.markdown(f"*{tier_label}*")
        cols = st.columns(len(tiers[tier_code]))
        for i, (price_key, price_val) in enumerate(tiers[tier_code].items()):
            label = price_key.replace("_perMeter", "/延米").replace("_perSqm", "/㎡") \
                             .replace("_perUnit", "/组").replace("_", " ")
            new_val = cols[i].number_input(
                label,
                min_value=0,
                value=int(price_val),
                step=50,
                key=f"admin_{code}_{tier_code}_{price_key}",
            )
            if new_val != int(price_val):
                tiers[tier_code][price_key] = new_val
                changed = True

    # ── 台面价格（有台面的品类） ───────────────────────────────
    if data.get("hasCountertop") and "countertop" in data:
        st.markdown("**台面价格（每延米）**")
        for ct_type, ct_prices in data["countertop"].items():
            st.markdown(f"*{ct_type}*")
            ct_cols = st.columns(3)
            for i, (t_code, t_label) in enumerate([("economy","经济款"),("quality","品质款"),("flagship","旗舰款")]):
                if t_code in ct_prices:
                    nv = ct_cols[i].number_input(
                        t_label, min_value=0, value=int(ct_prices[t_code]), step=50,
                        key=f"admin_{code}_ct_{ct_type}_{t_code}",
                    )
                    if nv != int(ct_prices[t_code]):
                        data["countertop"][ct_type][t_code] = nv
                        changed = True

    # ── 模块价格（橱柜） ──────────────────────────────────────
    if "modules" in data:
        st.markdown("**模块单价**")
        for mod in data["modules"]:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.markdown(f"<small>{mod['code']} {mod['name']}</small>", unsafe_allow_html=True)
            for i, (t_code, t_label) in enumerate([("economy","经济"),("quality","品质"),("flagship","旗舰")]):
                nv = [c2, c3, c4][i].number_input(
                    t_label, min_value=0, value=int(mod.get(t_code, 0)), step=50,
                    key=f"admin_{code}_mod_{mod['code']}_{t_code}",
                )
                if nv != int(mod.get(t_code, 0)):
                    mod[t_code] = nv
                    changed = True

    # ── 五金价格 ──────────────────────────────────────────────
    if "hardware" in data:
        st.markdown("**五金配件**")
        for hw_key, hw_val in data["hardware"].items():
            if isinstance(hw_val, dict):
                st.markdown(f"*{hw_key.replace('_', ' ')}*")
                hw_cols = st.columns(3)
                for i, (t_code, t_label) in enumerate([("economy","经济"),("quality","品质"),("flagship","旗舰")]):
                    nv = hw_cols[i].number_input(
                        t_label, min_value=0, value=int(hw_val.get(t_code, 0)), step=10,
                        key=f"admin_{code}_hw_{hw_key}_{t_code}",
                    )
                    if nv != int(hw_val.get(t_code, 0)):
                        data["hardware"][hw_key][t_code] = nv
                        changed = True

    # ── 工艺价格 ──────────────────────────────────────────────
    if "processes" in data:
        st.markdown("**特殊工艺**")
        proc_cols = st.columns(2)
        for i, (proc_key, proc_val) in enumerate(data["processes"].items()):
            col = proc_cols[i % 2]
            if isinstance(proc_val, (int, float)):
                nv = col.number_input(
                    proc_key.replace("_", " "), min_value=0, value=int(proc_val), step=50,
                    key=f"admin_{code}_proc_{proc_key}",
                )
                if nv != int(proc_val):
                    data["processes"][proc_key] = nv
                    changed = True

    # ── 配件价格（通用品类） ──────────────────────────────────
    if "accessories" in data:
        st.markdown("**特有配件**")
        acc_cols = st.columns(2)
        for i, (akey, aval) in enumerate(data["accessories"].items()):
            col = acc_cols[i % 2]
            if isinstance(aval, (int, float)):
                nv = col.number_input(
                    akey.replace("_", " "), min_value=0, value=int(aval), step=50,
                    key=f"admin_{code}_acc_{akey}",
                )
                if nv != int(aval):
                    data["accessories"][akey] = nv
                    changed = True

    # ── 保存按钮 ──────────────────────────────────────────────
    st.markdown("---")
    col_save, col_reset = st.columns([1, 3])
    if col_save.button("💾 保存修改", type="primary", key=f"save_{code}"):
        data["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
        data["updatedBy"]   = (st.session_state.get("user_info") or {}).get("username", "admin")
        data["version"]     = data.get("version", 1) + 1
        try:
            save_table(code, data)
            _log_change(code, old_data, data)
            st.success(f"✅ {CATEGORY_META[code]['name']} 价格已保存（版本 v{data['version']}）")
            st.rerun()
        except Exception as e:
            st.error(f"保存失败：{e}")

    if col_reset.button("↺ 放弃修改", key=f"reset_{code}"):
        st.rerun()

    # ── 版本信息 ──────────────────────────────────────────────
    st.caption(f"当前版本：v{data.get('version', 1)} · 最后更新：{data.get('lastUpdated', '—')} · 更新人：{data.get('updatedBy', '—')}")


# ═══════════════════════════════════════════════════════════════
# Tab 2 — 通用安装/工艺价格
# ═══════════════════════════════════════════════════════════════

def _tab_common_prices():
    try:
        data = load_common()
    except Exception as e:
        st.error(f"读取通用价格失败：{e}")
        return

    old_data = copy.deepcopy(data)
    changed = False

    st.markdown("**安装运输**")
    inst = data["install"]
    inst_cols = st.columns(2)
    for i, (k, v) in enumerate(inst.items()):
        nv = inst_cols[i % 2].number_input(
            k.replace("_", " "), min_value=0, value=int(v), step=50,
            key=f"admin_common_inst_{k}",
        )
        if nv != int(v):
            data["install"][k] = nv
            changed = True

    st.markdown("**通用特殊工艺**")
    proc = data.get("universal_processes", {})
    proc_cols = st.columns(2)
    for i, (k, v) in enumerate(proc.items()):
        nv = proc_cols[i % 2].number_input(
            k.replace("_", " "), min_value=0, value=int(v), step=50,
            key=f"admin_common_proc_{k}",
        )
        if nv != int(v):
            data["universal_processes"][k] = nv
            changed = True

    st.markdown("---")
    if st.button("💾 保存通用价格", type="primary", key="save_common"):
        data["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
        data["updatedBy"]   = (st.session_state.get("user_info") or {}).get("username", "admin")
        data["version"]     = data.get("version", 1) + 1
        try:
            save_common(data)
            _log_change("COMMON", old_data, data)
            st.success("✅ 通用价格已保存")
            st.rerun()
        except Exception as e:
            st.error(f"保存失败：{e}")

    st.caption(f"版本：v{data.get('version', 1)} · 最后更新：{data.get('lastUpdated', '—')}")


# ═══════════════════════════════════════════════════════════════
# Tab 3 — 变更日志
# ═══════════════════════════════════════════════════════════════

def _tab_change_log():
    logs = st.session_state.get(CHANGE_LOG_KEY, [])
    if not logs:
        st.info("本次会话暂无价格变更记录（每次保存后自动记录）")
        return

    st.markdown(f"共 **{len(logs)}** 条变更记录（本次会话）")
    for log in reversed(logs):
        with st.expander(f"{log['time']} — {log['category']} · {log['desc']}"):
            st.json(log["changes"])


def _log_change(category: str, old: dict, new: dict) -> None:
    changes = _diff(old, new)
    if not changes:
        return
    if CHANGE_LOG_KEY not in st.session_state:
        st.session_state[CHANGE_LOG_KEY] = []
    st.session_state[CHANGE_LOG_KEY].append({
        "time":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "desc":     f"修改了 {len(changes)} 项",
        "changes":  changes,
        "operator": (st.session_state.get("user_info") or {}).get("username", "admin"),
    })


def _diff(old: dict, new: dict, path="") -> dict:
    diffs = {}
    for k in set(list(old.keys()) + list(new.keys())):
        full = f"{path}.{k}" if path else k
        ov = old.get(k)
        nv = new.get(k)
        if isinstance(ov, dict) and isinstance(nv, dict):
            sub = _diff(ov, nv, full)
            diffs.update(sub)
        elif ov != nv:
            diffs[full] = {"before": ov, "after": nv}
    return diffs
