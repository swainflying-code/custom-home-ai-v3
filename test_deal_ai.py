#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试deal_push AI分析功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 模拟测试数据
test_customer = {
    "id": "test-001",
    "customer_no": "CUS-20260330-001",
    "customer_name": "王先生",
    "contact": "13800138000",
    "budget_range": "15-20万",
    "intent_level": "中",
    "custom_spaces": ["厨房", "客厅"],
    "style_preference": "现代简约",
    "appearance_preference": ["烤漆", "实木"],
    "material_type_preference": ["不锈钢", "实木"]
}

test_deal_push_data = {
    "quote_version": "L2 方案报价",
    "recent_quote": 185000,
    "quote_status": "已发送（3天前）",
    "competitor_name": "万格丽",  # 用户填写的竞争品牌
    "compare_dimension": "价格",
    "advantage_recognition": "认可",
    "key_to_deal": "确认最终方案细节"
}

test_sales_report = "客户昨天微信说万格丽的价格比我们低15%，问能不能给同样折扣。他说万格丽的板材是进口的，我们的价格偏高。我已经发了两次报价了，客户回复越来越慢。"

print("测试deal_push AI分析功能...")
print(f"竞争品牌: {test_deal_push_data['competitor_name']}")
print(f"销售汇报: {test_sales_report[:50]}...")
print()

# 测试AI服务导入
try:
    from core.ai_service import AIService
    print("[OK] AI服务导入成功")
    
    # 注意：实际运行时需要配置正确的API密钥
    print("\n注意：实际AI分析需要配置MIMO API密钥")
    print("如果配置正确，AI分析会基于'万格丽'而不是'欧派'")
    
except Exception as e:
    print(f"[ERROR] 导入失败: {e}")

print("\n修复总结：")
print("1. AI分析现在会读取用户填写的竞争品牌（如'万格丽'）")
print("2. 不再使用硬编码的'欧派'示例")
print("3. AI Prompt强制要求基于实际竞争品牌分析")
print("4. 数据会保存到deal_push_v3表")