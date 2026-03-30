"""
成交魔方 V3 — 预算锚定计算引擎
核心原则：AI 只负责「拆解」，所有价格数字从此引擎读取，AI 永远不碰价格。
"""

import json
import os
from pathlib import Path
from typing import Any

# ── 路径 ─────────────────────────────────────────────────────────────
_PRICING_DIR = Path(__file__).parent.parent / "pricing"

# ── 档位映射 ─────────────────────────────────────────────────────────
TIER_MAP = {
    "经济款": "economy",
    "品质款": "quality",
    "旗舰款": "flagship",
}
TIER_LABELS = list(TIER_MAP.keys())

# ── 预算区间映射（字符串 → 数值元组 (min, max)，单位元） ──────────────
BUDGET_RANGE_MAP = {
    "5万以下":    (0,      50000),
    "5-10万":    (50000,  100000),
    "10-20万":   (100000, 200000),
    "20-30万":   (200000, 300000),
    "30万以上":  (300000, 9999999),
    "未透露":    (0,       9999999),
}

# ── 品类定义 ─────────────────────────────────────────────────────────
CATEGORY_META = {
    "KC":  {"name": "橱柜",      "emoji": "🍳", "unit": "延米",    "file": "kc_benchmark.json"},
    "WD":  {"name": "衣柜",      "emoji": "👔", "unit": "投影面积", "file": "wd_benchmark.json"},
    "YG":  {"name": "阳台柜",    "emoji": "🏠", "unit": "延米",    "file": "yg_benchmark.json"},
    "JZ":  {"name": "家政柜",    "emoji": "🧹", "unit": "延米",    "file": "jz_benchmark.json"},
    "XG":  {"name": "鞋柜",      "emoji": "👟", "unit": "单组",    "file": "xg_benchmark.json"},
    "SN":  {"name": "收纳柜",    "emoji": "📦", "unit": "投影面积", "file": "sn_benchmark.json"},
    "CB":  {"name": "餐边柜",    "emoji": "🍷", "unit": "延米",    "file": "cb_benchmark.json"},
    "TG":  {"name": "厅柜/电视柜","emoji": "📺", "unit": "延米",    "file": "tg_benchmark.json"},
    "SH":  {"name": "书柜",      "emoji": "📚", "unit": "投影面积", "file": "sh_benchmark.json"},
    "JIU": {"name": "酒柜",      "emoji": "🍸", "unit": "投影面积", "file": "jiu_benchmark.json"},
}

# 空间关键词 → 推荐品类
SPACE_TO_CATEGORY = {
    "厨房":   ["KC"],
    "阳台":   ["YG"],
    "衣帽间": ["WD"],
    "餐厅":   ["CB"],
    "玄关":   ["XG"],
    "客厅":   ["TG"],
    "书房":   ["SH"],
    "卫生间": ["SN"],
}


# ═══════════════════════════════════════════════════════════════════
# 核心：读取价格表
# ═══════════════════════════════════════════════════════════════════

def load_table(category_code: str) -> dict:
    """读取某品类基准价 JSON（优先从 session_state 缓存读，兼顾管理员改价后立即生效）"""
    try:
        import streamlit as st
        cache_key = f"_price_table_{category_code}"
        if cache_key in st.session_state:
            return st.session_state[cache_key]
    except Exception:
        pass

    meta = CATEGORY_META.get(category_code)
    if not meta:
        raise ValueError(f"未知品类代码：{category_code}")
    fpath = _PRICING_DIR / meta["file"]
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_table(category_code: str, data: dict) -> None:
    """保存修改后的价格表到本地 JSON"""
    meta = CATEGORY_META.get(category_code)
    if not meta:
        raise ValueError(f"未知品类代码：{category_code}")
    fpath = _PRICING_DIR / meta["file"]
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 清除 session 缓存
    try:
        import streamlit as st
        cache_key = f"_price_table_{category_code}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    except Exception:
        pass


def load_common() -> dict:
    """读取通用安装/工艺价格"""
    fpath = _PRICING_DIR / "common_benchmark.json"
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_common(data: dict) -> None:
    fpath = _PRICING_DIR / "common_benchmark.json"
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# 计算函数
# ═══════════════════════════════════════════════════════════════════

def get_tier_key(tier_label: str) -> str:
    return TIER_MAP.get(tier_label, "quality")


def calc_kc(params: dict, tier_label: str = "品质款") -> dict:
    """橱柜计算（按模块清单 or 延米汇总）"""
    t = load_table("KC")
    tk = get_tier_key(tier_label)

    base_meters = float(params.get("base_meters", 0))
    wall_meters  = float(params.get("wall_meters", 0))
    countertop_meters = float(params.get("countertop_meters", base_meters))
    countertop_type   = params.get("countertop_type", "304_antiFingerprint")
    countertop_depth  = params.get("countertop_depth", "standard")  # standard / deep / waterfall
    modules           = params.get("modules", [])   # [{code, qty}]
    hardware_items    = params.get("hardware", [])  # [{key, qty}]
    processes         = params.get("processes", []) # [{key, value}]

    breakdown = {}

    # ① 主体（优先按模块，否则按延米）
    if modules:
        body = 0
        mod_map = {m["code"]: m for m in t["modules"]}
        for item in modules:
            mod = mod_map.get(item["code"])
            if mod:
                body += mod.get(tk, 0) * int(item.get("qty", 1))
        breakdown["柜体模块"] = body
    else:
        body = base_meters * t["tiers"][tk]["baseCabinet_perMeter"] \
             + wall_meters  * t["tiers"][tk]["wallCabinet_perMeter"]
        breakdown["柜体（延米）"] = body

    # ② 台面
    ct_price = t["countertop"].get(countertop_type, {}).get(tk, 0)
    coeff = 1.0
    if countertop_depth == "deep":
        coeff = t["countertopCoefficients"]["deep_650plus"]
    elif countertop_depth == "waterfall":
        coeff = t["countertopCoefficients"]["waterfall_edge"]
    countertop_total = countertop_meters * ct_price * coeff
    breakdown["台面"] = countertop_total

    # ③ 五金
    hw_total = 0
    hw_cfg = t["hardware"]
    for hw in hardware_items:
        key = hw.get("key", "")
        qty = float(hw.get("qty", 0))
        price_node = hw_cfg.get(key, {})
        unit_price = price_node.get(tk, 0) if isinstance(price_node, dict) else price_node
        hw_total += unit_price * qty
    breakdown["五金配件"] = hw_total

    # ④ 特殊工艺
    proc_total = 0
    proc_cfg = t["processes"]
    for proc in processes:
        key   = proc.get("key", "")
        value = float(proc.get("value", 0))
        raw = proc_cfg.get(key, 0)
        if isinstance(raw, dict):
            proc_total += (raw.get("min", 0) + raw.get("max", 0)) / 2 * (value or 1)
        else:
            proc_total += raw * (value or 1)
    breakdown["特殊工艺"] = proc_total

    total = sum(breakdown.values())
    return {"total": round(total), "breakdown": breakdown, "tier": tier_label}


def calc_wd(params: dict, tier_label: str = "品质款") -> dict:
    """衣柜计算（投影面积）"""
    t  = load_table("WD")
    tk = get_tier_key(tier_label)

    width  = float(params.get("width", 0))   # 宽（m）
    height = float(params.get("height", 0))  # 高（m）
    sqm    = width * height
    door_type       = params.get("door_type", "flatDoor")
    interior_pkg    = params.get("interior_pkg", "standard")
    door_qty        = int(params.get("door_qty", 0))
    processes       = params.get("processes", [])

    breakdown = {}

    # ① 主体
    body = sqm * t["tiers"][tk].get(f"{door_type}_perSqm", t["tiers"][tk]["flatDoor_perSqm"])
    breakdown["柜体主体"] = body

    # ② 内部配置包
    pkg_price = t["interiorPackages"].get(interior_pkg, {}).get("price", 0)
    if pkg_price:
        breakdown["内部配置包"] = pkg_price

    # ③ 门板升级
    door_cfg = t["doorUpgrades"].get(door_type, {})
    door_add = door_cfg.get("add_perSqm", 0) * sqm + door_cfg.get("add_perDoor", 0) * door_qty
    if door_add:
        breakdown["门板升级"] = door_add

    # ④ 工艺
    proc_total = 0
    proc_cfg = t["processes"]
    for proc in processes:
        key   = proc.get("key", "")
        value = float(proc.get("value", 0))
        raw = proc_cfg.get(key, 0)
        if isinstance(raw, dict):
            proc_total += (raw.get("min", 0) + raw.get("max", 0)) / 2 * (value or 1)
        else:
            proc_total += raw * (value or 1)
    if proc_total:
        breakdown["特殊工艺"] = proc_total

    total = sum(breakdown.values())
    return {"total": round(total), "breakdown": breakdown, "tier": tier_label}


def _linear_cabinet_calc(category_code: str, params: dict, tier_label: str) -> dict:
    """通用延米品类计算（YG/JZ/CB/TG）"""
    t  = load_table(category_code)
    tk = get_tier_key(tier_label)

    meters    = float(params.get("meters", 0))
    sub_type  = params.get("sub_type", list(t["tiers"][tk].keys())[0])
    accessories = params.get("accessories", [])

    breakdown = {}

    price_key = sub_type
    body = meters * t["tiers"][tk].get(price_key, 0)
    breakdown["柜体主体"] = body

    acc_cfg = t.get("accessories", {})
    acc_total = 0
    for acc in accessories:
        key   = acc.get("key", "")
        qty   = float(acc.get("qty", 1))
        raw   = acc_cfg.get(key, 0)
        if isinstance(raw, dict):
            acc_total += (raw.get("min", 0) + raw.get("max", 0)) / 2 * qty
        else:
            acc_total += raw * qty
    if acc_total:
        breakdown["配件"] = acc_total

    total = sum(breakdown.values())
    return {"total": round(total), "breakdown": breakdown, "tier": tier_label}


def _area_cabinet_calc(category_code: str, params: dict, tier_label: str) -> dict:
    """通用投影面积品类计算（SN/SH/JIU）"""
    t  = load_table(category_code)
    tk = get_tier_key(tier_label)

    width  = float(params.get("width", 0))
    height = float(params.get("height", 0))
    sqm    = width * height
    sub_type    = params.get("sub_type", list(t["tiers"][tk].keys())[0])
    accessories = params.get("accessories", [])

    breakdown = {}

    body = sqm * t["tiers"][tk].get(sub_type, 0)
    breakdown["柜体主体"] = body

    acc_cfg = t.get("accessories", {})
    acc_total = 0
    for acc in accessories:
        key   = acc.get("key", "")
        qty   = float(acc.get("qty", 1))
        raw   = acc_cfg.get(key, 0)
        if isinstance(raw, dict):
            acc_total += (raw.get("min", 0) + raw.get("max", 0)) / 2 * qty
        else:
            acc_total += raw * qty
    if acc_total:
        breakdown["配件"] = acc_total

    total = sum(breakdown.values())
    return {"total": round(total), "breakdown": breakdown, "tier": tier_label}


def _unit_cabinet_calc(category_code: str, params: dict, tier_label: str) -> dict:
    """单组品类计算（XG）"""
    t  = load_table(category_code)
    tk = get_tier_key(tier_label)

    qty       = int(params.get("qty", 1))
    sub_type  = params.get("sub_type", "standard_perUnit")
    accessories = params.get("accessories", [])

    breakdown = {}

    body = qty * t["tiers"][tk].get(sub_type, 0)
    breakdown["柜体主体"] = body

    acc_cfg = t.get("accessories", {})
    acc_total = 0
    for acc in accessories:
        key   = acc.get("key", "")
        qty_a = float(acc.get("qty", 1))
        raw   = acc_cfg.get(key, 0)
        if isinstance(raw, dict):
            acc_total += (raw.get("min", 0) + raw.get("max", 0)) / 2 * qty_a
        else:
            acc_total += raw * qty_a
    if acc_total:
        breakdown["配件"] = acc_total

    total = sum(breakdown.values())
    return {"total": round(total), "breakdown": breakdown, "tier": tier_label}


# ── 统一计算入口 ──────────────────────────────────────────────────
CALC_ROUTER = {
    "KC":  calc_kc,
    "WD":  calc_wd,
    "YG":  lambda p, t: _linear_cabinet_calc("YG",  p, t),
    "JZ":  lambda p, t: _linear_cabinet_calc("JZ",  p, t),
    "CB":  lambda p, t: _linear_cabinet_calc("CB",  p, t),
    "TG":  lambda p, t: _linear_cabinet_calc("TG",  p, t),
    "XG":  lambda p, t: _unit_cabinet_calc("XG",   p, t),
    "SN":  lambda p, t: _area_cabinet_calc("SN",   p, t),
    "SH":  lambda p, t: _area_cabinet_calc("SH",   p, t),
    "JIU": lambda p, t: _area_cabinet_calc("JIU",  p, t),
}


def calculate(category_code: str, params: dict, tier_label: str = "品质款") -> dict:
    """统一计算入口，返回 {total, breakdown, tier}"""
    fn = CALC_ROUTER.get(category_code)
    if not fn:
        raise ValueError(f"不支持的品类：{category_code}")
    result = fn(params, tier_label)
    return result


def add_install(result: dict, install_type: str = "linear",
                quantity: float = 1.0, location: str = "urban",
                floor_type: str = "elevator") -> dict:
    """追加安装运输费用"""
    common = load_common()
    inst   = common["install"]

    transport = (inst["urban_transport_min"] + inst["urban_transport_max"]) / 2
    if install_type == "linear":
        install_cost = quantity * inst["install_perMeter_linear"]
    elif install_type == "area":
        install_cost = quantity * inst["install_perSqm_area"]
    else:
        install_cost = quantity * inst["install_perUnit"]

    extra = 0
    if floor_type == "no_elevator":
        extra = (inst["highFloor_noElevator_min"] + inst["highFloor_noElevator_max"]) / 2
    elif floor_type == "remote":
        extra = (inst["remote_area_min"] + inst["remote_area_max"]) / 2

    install_total = round(transport + install_cost + extra)
    result["breakdown"]["安装运输"] = install_total
    result["total"] = round(result["total"] + install_total)
    return result


# ── 预算校验 ─────────────────────────────────────────────────────
def budget_check(grand_total: float, budget_str: str) -> dict:
    """
    返回 {status: 'ok'/'over'/'under', ratio, msg, suggestions}
    """
    lo, hi = BUDGET_RANGE_MAP.get(budget_str, (0, 9999999))
    if hi >= 9999999:
        return {"status": "ok", "ratio": None, "msg": "预算未设限", "suggestions": []}

    if grand_total <= hi:
        if grand_total >= lo:
            ratio = grand_total / hi
            msg = f"✅ 报价 ¥{grand_total:,.0f}，落在预算区间 {budget_str} 内"
            return {"status": "ok", "ratio": ratio, "msg": msg, "suggestions": []}
        else:
            msg = f"💡 报价 ¥{grand_total:,.0f}，低于预算下限，可考虑升档"
            return {"status": "under", "ratio": grand_total / lo if lo else 0, "msg": msg, "suggestions": []}
    else:
        over_by = grand_total - hi
        ratio = grand_total / hi
        msg = f"⚠️ 报价 ¥{grand_total:,.0f}，超出预算上限 ¥{over_by:,.0f}"
        suggestions = [
            "可将部分品类从品质款降至经济款",
            "减少附件和特殊工艺项",
            "缩减部分柜体延米/面积",
        ]
        return {"status": "over", "ratio": ratio, "msg": msg, "suggestions": suggestions}


def recommend_categories(spaces: list) -> list:
    """根据 B 模块选择的空间，推荐品类列表"""
    codes = []
    for sp in (spaces or []):
        for k, v in SPACE_TO_CATEGORY.items():
            if k in sp:
                for c in v:
                    if c not in codes:
                        codes.append(c)
    return codes


def format_price_range(total: float, precision: float = 0.10) -> str:
    lo = round(total * (1 - precision) / 100) * 100
    hi = round(total * (1 + precision) / 100) * 100
    return f"¥{lo:,.0f} ~ ¥{hi:,.0f}"
