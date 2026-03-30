"""
成交魔方 V3 - AI服务层
支持：主卡 Prompt（销售必看）、详情 Prompt（细致分析）、周报 Prompt（老板周报）
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import openai
from .config import config
from .cache import cache_result

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    pass


# ================================================================
# Prompt 模板定义
# ================================================================

PROMPT_CARD = """你是一个定制家居门店的"销售教练"，有20年门店成交经验。
根据销售刚刚接待完的客户信息，请用最短的语言，给销售一个"立即行动卡"。

【客户信息】
{customer_info}

【输出要求——严格遵守】
格式必须如下（不要添加任何额外内容）：

客户一句话画像（5字以内）：xxx
意向等级: [🟢高意向 / 🟡中意向 / 🔴低意向]

客户最在意的3件事（按重要性排）:
1. xxx
2. xxx
3. xxx

下一步动作（一句话）:[具体做什么，比如"3天内打电话约看样品"]

跟进话术（直接能发给客户的微信/能说的话，不超过50字）:"xxx"

可能的一个坑（最容易丢这单的一个风险点，一句话）:xxx

【判断意向等级的规则】
🟢 高意向（满足以下任意一组）:

【客户信息】
{customer_info}

【输出要求——严格遵守】
格式必须如下（不要添加任何额外内容）：

客户一句话画像（5字以内）：xxx
意向等级: [🟢高意向 / 🟡中意向 / 🔴低意向]

客户最在意的3件事（按重要性排）:
1. xxx
2. xxx
3. xxx

下一步动作（一句话）:[具体做什么，比如"3天内打电话约看样品"]

跟进话术（直接能发给客户的微信/能说的话，不超过50字）:"xxx"

可能的一个坑（最容易丢这单的一个风险点，一句话）:xxx

【判断意向等级的规则】
🟢 高意向（满足以下任意一组）:
  A组: 预算明确 + 决策人在场 + 已预约下一步
  B组: 已上门量房/已出方案 + 决策人在场（无论是否透露预算）
  C组: 主动提及工期紧迫/已入住状态 + 预算明确
🟡 中意向: 有兴趣但有明显犹豫点（预算模糊/决策人不在/在比较竞品/首次到店未预约下一步）
🔴 低意向: 随便看看/预算严重不匹配/无明确需求/明显抗拒

【铁律】
1. 全部内容加起来不超过300字
2. 禁止使用任何学术术语（马斯洛、卡尼曼、SPIN、损失厌恶等一律不能出现）
3. 禁止使用"建议"、"可以考虑"等模糊词——必须是确定的动作
4. 跟进话术必须像朋友发微信，包含一个"钩子"（案例图/活动/限量/同小区案例），绝对禁止出现"打扰了"、"冒昧联系"、"请问您考虑得怎么样了"
5. 不要输出"综合评分"、"成交概率百分比"这种数字
6. 如果"下一步计划"=暂不跟进 且 "离店状态"=犹豫/抗拒/不满，必须在"可能的坑"里标注: "⛔ 此客户有流失风险，建议72小时内做一次轻触达（发案例图/到店活动通知），不要让沉默变成拒绝。"
"""

PROMPT_DETAIL = """你是一个定制家居门店的"销售教练"，有20年门店成交经验，特别懂怎么搞定犹豫不决的客户。
以下是客户信息和第一步的简要分析。现在请展开详细分析，帮助销售更深入地理解这个客户。

【客户信息】
{customer_info}

【第一步简要分析（保持一致）】
{card_result}

【请输出以下5个板块，每个板块不超过100字】

═══ 1. 这个人怎么想的 ═══
用大白话描述这个客户的心理状态。禁止用"消费者画像"、"决策模型"等术语。像跟同事聊天一样说人话。

═══ 2. 钱的事 ═══
这个客户的预算够不够？如果不够，缺口在哪？怎么引导？

═══ 3. 怎么搞定这个客户 ═══
给3条具体战术，每条一句话，销售明天就能用。
分别覆盖：
- 第1条: 下次联系时（微信/电话）怎么做
- 第2条: 客户再到店时怎么做
- 第3条: 如果客户开始犹豫/比价，怎么应对

═══ 4. 竞品攻防 ═══
A. 如果知道竞品：他可能在看谁？你的差异化打法是什么？
B. 如果不知道竞品：给一个"万能防守话术"，帮销售在下次跟进时自然挖出竞品信息。

═══ 5. 时间窗口 ═══
这个客户什么时候会做决定？什么时候必须跟进？

【铁律】
1. 每个板块不超过100字
2. 全程大白话，禁止学术术语
3. 给的是"判断"和"动作"，不是"分析报告"
4. 如果某个板块信息不足判断，直接说"信息不足，跟进时重点了解：xxx"，不要编造
"""

PROMPT_WEEKLY = """你是一个定制家居门店的运营数据分析师。以下是本周门店客户数据汇总，请生成一份老板看的周报。

【本周数据】
{weekly_data}

【输出格式】
📋 本周成交率报告
进店 {total_visits} 组 → 成交 {total_deals} 组（成交率 {deal_rate}%）
📊 周环比: 进店{visit_change} / 成交{deal_change} / 跟进率{followup_change}

🔥 高意向客户跟进情况:
- 共 {high_intent_count} 组高意向，已跟进 {followed_count} 组，未跟进 {not_followed_count} 组
- ⚠️ 以下客户再不跟就凉了: {urgent_customers}

💰 本周漏了多少:
- 3天以上未跟进的客户 {overdue_count} 组，按平均客单价估算，潜在损失约 {potential_loss} 万元

✅ 做得好的（最多2条）:
{highlights}

⚠️ 需要关注的（最多2条）:
{concerns}

🎯 本周唯一建议（一句话）: {top_suggestion}

【铁律】
1. 全部内容不超过300字
2. 老板只关心三件事：成交了多少、漏了多少、谁该管——围绕这三件事说
3. 数字必须准确，不要模糊
4. 语气直接，老板没时间看客套话
"""


# ================================================================
# AI Service Class
# ================================================================

class AIService:
    """成交魔方 V3 AI服务"""

    def __init__(self):
        try:
            self.client = openai.OpenAI(
                api_key=config.ai.api_key,
                base_url=config.ai.base_url
            )
            self.model = config.ai.model
            logger.info(f"AI服务初始化成功，模型: {self.model}")
        except Exception as e:
            logger.error(f"AI服务初始化失败: {e}")
            raise AIServiceError(f"AI服务初始化失败: {e}")

    def _format_customer_info(self, data: Dict[str, Any]) -> str:
        """将客户表单数据格式化为可读文本"""
        lines = []
        label_map = {
            # A 板块
            "customer_name": "客户姓名",
            "contact": "联系方式",
            "customer_no": "顾客编号",
            "age_range": "年龄段",
            "visit_count": "到店次数",
            "source_channel": "来源渠道",
            "source_note": "来源备注",
            "house_type": "房屋类型",
            "house_area": "房屋区域",
            "renovation_type": "装修类型",
            "renovation_stage": "装修阶段",
            "order_timeline": "预计下单时间",
            "custom_spaces": "定制空间",
            "budget_range": "定制预算",
            # B 板块
            "visitor_identity": "到店身份",
            "decision_maker": "最终拍板人",
            "companion_type": "同行角色",
            "next_step": "下一步计划",
            "next_followup_date": "下次跟进时间",
            # C 板块
            "style_preference": "风格倾向",
            "appearance_preference": "外观质感倾向",
            "material_type_preference": "板材材质倾向",
            "focus_points": "最关注点",
            "compare_brands": "是否对比品牌",
            "family_size": "家庭人数",
        }
        for key, label in label_map.items():
            val = data.get(key)
            if val and val not in ("", [], None, "未知", "不明确"):
                if isinstance(val, list):
                    val = "、".join(val)
                lines.append(f"{label}：{val}")
        return "\n".join(lines) if lines else "（无客户信息）"

    def analyze_card(self, customer_data: Dict[str, Any]) -> str:
        """主卡分析（销售必看）"""
        try:
            customer_info = self._format_customer_info(customer_data)
            prompt = PROMPT_CARD.replace("{customer_info}", customer_info)
            
            # 调试：打印请求信息
            logger.info(f"analyze_card 请求: 模型={self.model}, prompt长度={len(prompt)}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000  # 增加到 1000 个 token
            )
            
            result = response.choices[0].message.content or "AI返回为空"
            
            # 调试：打印响应信息
            logger.info(f"analyze_card 响应: 长度={len(result)}, 是否完成={not response.choices[0].finish_reason == 'length'}")
            
            # 检查是否因长度被截断
            if response.choices[0].finish_reason == 'length':
                logger.warning(f"AI 响应被长度截断，可能需要增加 max_tokens")
                result += "\n\n⚠️ 注：AI 分析可能因长度限制被截断，请检查配置"
            
            return result
        except Exception as e:
            logger.error(f"主卡分析失败: {e}", exc_info=True)
            return f"❌ AI分析失败：{str(e)}"

    def analyze_detail(self, customer_data: Dict[str, Any], card_result: str) -> str:
        """详情分析（细致五板块）"""
        try:
            customer_info = self._format_customer_info(customer_data)
            prompt = PROMPT_DETAIL.replace("{customer_info}", customer_info).replace("{card_result}", card_result)
            
            # 调试：打印请求信息
            logger.info(f"analyze_detail 请求: 模型={self.model}, prompt长度={len(prompt)}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500  # 增加到 1500 个 token
            )
            
            result = response.choices[0].message.content or "AI返回为空"
            
            # 调试：打印响应信息
            logger.info(f"analyze_detail 响应: 长度={len(result)}, 是否完成={not response.choices[0].finish_reason == 'length'}")
            
            # 检查是否因长度被截断
            if response.choices[0].finish_reason == 'length':
                logger.warning(f"AI 详情响应被长度截断，可能需要增加 max_tokens")
                result += "\n\n⚠️ 注：AI 详情分析可能因长度限制被截断，请检查配置"
            
            return result
        except Exception as e:
            logger.error(f"详情分析失败: {e}", exc_info=True)
            return f"❌ AI分析失败：{str(e)}"

    def analyze_deal_push(self, customer_data: Dict[str, Any], deal_push_data: Dict[str, Any], sales_report: str) -> str:
        """成交推进AI分析（成交战地参谋）"""
        try:
            # 格式化客户基础信息
            customer_info = self._format_customer_info(customer_data)
            
            # 格式化deal_push信息
            deal_info_lines = []
            if deal_push_data.get("quote_version"):
                deal_info_lines.append(f"报价版本: {deal_push_data.get('quote_version')}")
            if deal_push_data.get("recent_quote"):
                deal_info_lines.append(f"最近报价: {deal_push_data.get('recent_quote')}元")
            if deal_push_data.get("quote_status"):
                deal_info_lines.append(f"报价状态: {deal_push_data.get('quote_status')}")
            if deal_push_data.get("bargain_info"):
                deal_info_lines.append(f"讨价还价: {deal_push_data.get('bargain_info')}")
            if deal_push_data.get("competitor_name"):
                deal_info_lines.append(f"竞争品牌: {deal_push_data.get('competitor_name')}")
            if deal_push_data.get("compare_dimension"):
                deal_info_lines.append(f"竞品比较维度: {deal_push_data.get('compare_dimension')}")
            if deal_push_data.get("advantage_recognition"):
                deal_info_lines.append(f"优势认可: {deal_push_data.get('advantage_recognition')}")
            if deal_push_data.get("key_to_deal"):
                deal_info_lines.append(f"成交关键: {deal_push_data.get('key_to_deal')}")
            
            deal_info = "\n".join(deal_info_lines) if deal_info_lines else "（暂无成交推进信息）"
            
            # Deal Push专用Prompt
            prompt = f"""你是一个定制家居行业的"成交战地参谋"，专门帮助销售在最后成交阶段拿下订单。你有15年终端销售经验，精通价格博弈、竞品拆解、客户心理把握。

【当前客户基础信息】
{customer_info}

【成交推进数据】
{deal_info}

【销售这次的'战况汇报'】
{sales_report}

【输出要求——严格遵守格式】
请按以下四部分输出，不要添加任何额外内容：

**🎯 一句话判断**
（一句话点出当前处境，如：客户在竞品间犹豫，拿价格施压，但核心关注点其实是XXXX）

**🗣️ 下一次话术（能直接用）**
（具体到可以直接发给客户的微信内容，不超过100字，要自然、真实、不机械）

**⚔️ 异议拆弹**
（如果客户提到竞品，就针对这个竞品进行拆解）
异议: "竞品的XX点比你们好"
拆解: （分析客户为什么这样说，背后的真实顾虑）
打法: （具体怎么应对，要口语化，能直接说）

**📅 跟进节奏建议**
- 今天: （具体动作）
- 3天内: （如果客户没回复，怎么跟进）
- 7天兜底: （如果还没进展，最后的备选方案）

【铁律】
1. 必须基于竞争品牌信息（如客户提到"万格丽"就分析万格丽，不要假设欧派）
2. 话术要真实销售口吻，不要"您好，我是XX"这种开场
3. 如果客户没提竞品，就专注挖掘他的真实顾虑
4. 每部分不超过150字，总字数不超过600字
5. 不要使用学术术语（马斯洛/卡尼曼等），用销售大白话"""

            logger.info(f"analyze_deal_push 请求: prompt长度={len(prompt)}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=1200
            )
            
            result = response.choices[0].message.content or "AI返回为空"
            logger.info(f"analyze_deal_push 响应: 长度={len(result)}")
            
            return result
        except Exception as e:
            logger.error(f"成交推进AI分析失败: {e}", exc_info=True)
            return f"❌ 成交推进AI分析失败：{str(e)}"

    def generate_weekly_report(self, weekly_stats: Dict[str, Any]) -> str:
        """老板周报生成"""
        try:
            # 构建周报数据文本
            data_text = json.dumps(weekly_stats, ensure_ascii=False, indent=2)
            prompt = f"""你是一个定制家居门店的运营数据分析师。以下是本周门店客户数据汇总，请生成一份老板看的周报。

【本周数据】
{data_text}

【输出格式严格如下】
📋 本周成交率报告
进店 X 组 → 成交 X 组（成交率 X%）
📊 周环比: 进店↑↓X% / 成交↑↓X% / 跟进率↑↓X%

🔥 高意向客户跟进情况:
- 共 X 组高意向，已跟进 X 组，未跟进 X 组
- ⚠️ 以下客户再不跟就凉了: [列出客户名+未跟进天数，无则写"暂无"]

💰 本周漏了多少:
- 3天以上未跟进的客户 X 组，按平均客单价估算，潜在损失约 X 万元

✅ 做得好的（最多2条，没有就不写）:
- xxx

⚠️ 需要关注的（最多2条，没有就不写）:
- xxx

🎯 本周唯一建议（一句话）: xxx

【铁律】
1. 全部内容不超过300字
2. 老板只关心：成交了多少、漏了多少、谁该管
3. 数字必须准确，不要模糊
4. 语气直接，没时间看客套话
"""
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            return response.choices[0].message.content or "AI返回为空"
        except Exception as e:
            logger.error(f"周报生成失败: {e}")
            return f"❌ 周报生成失败：{str(e)}"

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = None, max_tokens: int = None) -> str:
        """通用对话接口"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or config.ai.temperature,
                max_tokens=max_tokens or config.ai.max_tokens
            )
            result = response.choices[0].message.content
            if not result:
                raise AIServiceError("AI返回内容为空")
            return result
        except Exception as e:
            raise AIServiceError(f"AI对话失败: {e}")


# 全局实例（延迟初始化，避免启动时 config 未就绪）
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
