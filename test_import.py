#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证所有模块导入正常
"""

print("正在测试成交魔方 V3 所有模块导入...")

# 测试导入核心模块
try:
    import core.config
    print("[OK] core.config 导入成功")
except Exception as e:
    print(f"[ERROR] core.config 导入失败: {e}")

try:
    import core.database
    print("[OK] core.database 导入成功")
except Exception as e:
    print(f"[ERROR] core.database 导入失败: {e}")

try:
    import core.ai_service
    print("[OK] core.ai_service 导入成功")
except Exception as e:
    print(f"[ERROR] core.ai_service 导入失败: {e}")

try:
    import core.auth
    print("[OK] core.auth 导入成功")
except Exception as e:
    print(f"[ERROR] core.auth 导入失败: {e}")

# 测试导入页面模块
try:
    import pages.customer_diagnosis
    print("[OK] pages.customer_diagnosis 导入成功")
except Exception as e:
    print(f"[ERROR] pages.customer_diagnosis 导入失败: {e}")

try:
    import pages.solution_guide
    print("[OK] pages.solution_guide 导入成功")
except Exception as e:
    print(f"[ERROR] pages.solution_guide 导入失败: {e}")

try:
    import pages.budget_anchor
    print("[OK] pages.budget_anchor 导入成功")
except Exception as e:
    print(f"[ERROR] pages.budget_anchor 导入失败: {e}")

try:
    import pages.deal_push
    print("[OK] pages.deal_push 导入成功")
except Exception as e:
    print(f"[ERROR] pages.deal_push 导入失败: {e}")

# 测试导入工具模块
try:
    import utils.validators
    print("[OK] utils.validators 导入成功")
except Exception as e:
    print(f"[ERROR] utils.validators 导入失败: {e}")

try:
    import utils.formatters
    print("[OK] utils.formatters 导入成功")
except Exception as e:
    print(f"[ERROR] utils.formatters 导入失败: {e}")

print("\n测试完成！")