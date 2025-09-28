#!/usr/bin/env python3
"""
Generate persona-driven survey responses for V2 sample inputs, with
segment-aware patterns and scenario knobs to surface insights.

Usage:
  python tools/generate_v2_persona_responses.py \
    --input data/V2-sample-product-survey-input.json \
    --output data/V2-sample-product-survey-input-100.json \
    --count 100 --scenario auto

Notes:
  - Uses factor lists from the input file to ensure valid options.
  - Personas influence NPS score distribution, factor selection, and open text.
  - Generates plausible metadata and timestamps; no external network required.
"""
from __future__ import annotations

import argparse
import json
import random
import string
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional


def _rand_id(n: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=n))


def _dt_range(start: datetime, i: int, step_sec: int = 75) -> Tuple[str, str, str]:
    st = start + timedelta(seconds=i * step_sec)
    dur = random.randint(20, 180)
    et = st + timedelta(seconds=dur)
    def fmt(d: datetime) -> str:
        return d.strftime("%Y-%m-%dT%H:%M:%S")
    def fmt_dur(s: int) -> str:
        m, s = divmod(s, 60)
        if m == 0:
            return f"{s}秒"
        return f"{m}分钟{s}秒"
    return fmt(st), fmt(et), fmt_dur(dur)


def _categorize(score: int) -> str:
    if score <= 6:
        return "detractor"
    if score <= 8:
        return "passive"
    return "promoter"


def _weighted_choice(pairs: List[Tuple[Any, float]]):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


def build_personas(survey_type: str, factors_pos: List[str], factors_neg: List[str]):
    if survey_type == "product_nps":
        return [
            {
                "name": "年轻白领-口味党",
                "weight": 0.20,
                "score_dist": [(9, 2), (10, 3), (8, 1)],
                "pos": ["产品口味口感好", "包装设计好（如醒目、美观，材质好，便携、方便打开等）", "对促销活动满意（如赠品、活动力度/规则等）"],
                "neg": [],
                "pos_text": ["口味丰富不腻，早餐/下午茶都合适。", "新款口味惊喜，包装好看易携带。", "顺滑清爽，搭配麦片很适合。"],
                "neg_text": [""],
            },
            {
                "name": "价格敏感-宝妈/宝爸",
                "weight": 0.18,
                "score_dist": [(7, 2), (8, 3), (9, 1)],
                "pos": ["产品物有所值、性价比高", "物流配送、门店导购、售后等服务体验好"],
                "neg": ["促销活动不好（如对赠品、活动力度/规则等不满意)", "产品价格太贵，性价比不高"],
                "pos_text": ["活动合适就会多囤一点，性价比高。"],
                "neg_text": ["促销不够给力，家庭开销压力大。", "价格如果再友好一点会回购更多。"],
            },
            {
                "name": "乳糖不耐-健康关注",
                "weight": 0.16,
                "score_dist": [(5, 3), (6, 2), (7, 1)],
                "pos": ["饮用后体感舒适，无不良反应"],
                "neg": ["饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应)", "没有感知到产品宣传的功能"],
                "pos_text": ["低乳糖款更适合我，体感舒适。", "喝完没有负担，消化轻松。"],
                "neg_text": ["偶尔还是不太舒服，功能感知也一般。", "标注是低乳糖，但体感差异不明显。"],
            },
            {
                "name": "品牌忠诚-资深用户",
                "weight": 0.18,
                "score_dist": [(9, 2), (10, 2), (8, 1)],
                "pos": ["喜欢品牌或代言人、赞助综艺等宣传内容", "产品口味口感好", "产品物有所值、性价比高"],
                "neg": [],
                "pos_text": ["一直买这牌子，口味稳定，家人都喜欢。", "买了很多年，品质稳定放心。"],
                "neg_text": [""],
            },
            {
                "name": "质量敏感-谨慎型",
                "weight": 0.13,
                "score_dist": [(4, 2), (5, 2), (6, 1)],
                "pos": [],
                "neg": ["产品品质不稳定性（如发生变质、有异物等)", "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等)"],
                "pos_text": [""],
                "neg_text": ["之前遇到过质量问题，仍有顾虑。", "开封体验一般，包装不太好开。"],
            },
            {
                "name": "宣传反感-务实型",
                "weight": 0.13,
                "score_dist": [(3, 2), (5, 2), (6, 1)],
                "pos": [],
                "neg": ["不喜欢品牌或代言人、赞助综艺等宣传内容", "没有感知到产品宣传的功能"],
                "pos_text": [""],
                "neg_text": ["宣传过多不接地气，希望少些噱头。", "广告词太花哨，实际体验一般。"],
            },
        ]
    else:  # system_platform
        return [
            {
                "name": "产品经理-效率导向",
                "weight": 0.22,
                "score_dist": [(8, 1), (9, 2), (10, 2)],
                "pos": ["能高效完成任务", "功能完善", "内容质量高"],
                "neg": [],
                "exp_text": ["增加需求模板与最佳实践案例。", "沉淀项目复盘与模板库。"],
                "sug_text": ["优化关键路径的点击步骤。", "缩短发布链路，减少重复填写。"],
            },
            {
                "name": "新同事-上手困难",
                "weight": 0.18,
                "score_dist": [(5, 2), (6, 2), (7, 1)],
                "pos": ["界面清晰易理解"],
                "neg": ["操作复杂难上手", "功能难找"],
                "exp_text": ["提供新手引导和任务清单。", "给出按角色的上手路线图。"],
                "sug_text": ["入口层级再扁平一些。", "把常用功能放到首页快捷区。"],
            },
            {
                "name": "运营-内容导向",
                "weight": 0.16,
                "score_dist": [(7, 1), (8, 2), (9, 1)],
                "pos": ["内容质量高", "内容时效性高", "活动丰富"],
                "neg": ["内容更新滞后", "活动单调"],
                "exp_text": ["加强活动复盘与行业动态。", "沉淀营销物料与复用指南。"],
                "sug_text": ["提升专题内容更新频率。", "活动专题做成合集，便于检索。"],
            },
            {
                "name": "销售-业务实用",
                "weight": 0.18,
                "score_dist": [(6, 1), (7, 2), (8, 2)],
                "pos": ["数据有帮助", "应用与服务介绍清晰"],
                "neg": ["数据帮助不大"],
                "exp_text": ["提供更多一线案例与话术库。", "按行业拆分竞品与案例库。"],
                "sug_text": ["细化行业方案的落地指南。", "加强移动端表格展示体验。"],
            },
            {
                "name": "技术-稳定优先",
                "weight": 0.14,
                "score_dist": [(7, 1), (8, 1), (9, 1)],
                "pos": ["性能稳定", "功能完善"],
                "neg": ["性能不稳定"],
                "exp_text": ["开放接口监控与告警面板。", "提供变更日志与SLA。"],
                "sug_text": ["暴露更多技术指标与状态。", "支持导出慢查询明细。"],
            },
            {
                "name": "管理者-概览需要",
                "weight": 0.12,
                "score_dist": [(8, 1), (9, 1), (7, 1)],
                "pos": ["界面美观", "内容很丰富"],
                "neg": ["界面内容不清晰"],
                "exp_text": ["沉淀管理驾驶舱，支持对比分析。", "提供目标进度与预警。"],
                "sug_text": ["简化首页信息层级。", "仪表盘支持自定义视图。"],
            },
        ]


def _choose_scores(score_dist: List[Tuple[int, int]]) -> int:
    # Convert to weighted list
    pairs = []
    for score, w in score_dist:
        pairs.append((score, w))
    return _weighted_choice(pairs)


def _clamp_factors(choices: List[str], allowed: List[str], max_k: int) -> List[str]:
    filtered = [c for c in choices if c in allowed]
    if not filtered:
        return []
    k = random.randint(1, min(max_k, len(filtered)))
    return random.sample(filtered, k)


def generate_responses(doc: Dict[str, Any], count: int, scenario: Optional[str] = None) -> Dict[str, Any]:
    out = deepcopy(doc)
    sr = out["survey_response_data"]
    survey_type = sr["survey_metadata"]["survey_type"]
    factors_neg = sr["survey_config"]["factor_questions"]["negative_factors"]["factor_list"]
    factors_pos = sr["survey_config"]["factor_questions"]["positive_factors"]["factor_list"]
    personas = build_personas(survey_type, factors_pos, factors_neg)

    responses = []
    # Start time reference: use export_timestamp if present, else now
    base_ts = sr["survey_metadata"].get("export_timestamp")
    try:
        base_dt = datetime.fromisoformat(base_ts.replace("Z", "")) if base_ts else datetime.now()
    except Exception:
        base_dt = datetime.now()

    # Weighted pool of personas
    weighted_personas = [(p, p["weight"]) for p in personas]

    # Optional brand list for product text enrichment
    brand_names: List[str] = []
    if survey_type == "product_nps":
        try:
            with open("data/洞察智能体品类品牌渠道清单.json", "r", encoding="utf-8") as bf:
                brand_doc = json.load(bf)
                for bu in brand_doc.get("business_units", []):
                    for p in bu.get("products", []):
                        name = p.get("brand_name")
                        if name:
                            brand_names.append(name)
        except Exception:
            brand_names = ["伊利", "金典", "安慕希", "舒化"]

    # Lexicons for varied wording
    taste_adjs = ["醇厚", "清爽", "不腻", "顺滑", "香浓", "细腻", "有奶香", "不甜腻"]
    scenarios = ["早餐", "下午茶", "加班", "健身后", "孩子上学前", "通勤路上", "周末郊游"]
    pack_phrases = ["易撕口", "便携", "环保材质", "外观高级", "盒盖结实", "不漏奶"]
    neg_adjs = ["偏甜", "有点贵", "不太好开", "活动少", "宣传过头", "功能感一般", "配送慢", "分层", "结块"]
    improv_phrases = ["增加无糖/低糖选项", "多做些满减", "改进开口设计", "提升到货速度", "少点花哨宣传"]

    # Synonyms to help clustering around themes
    packaging_syn = ["封口难", "开口设计不友好", "容易漏", "携带不便", "包装不结实"]
    price_syn = ["有点贵", "价位偏高", "性价比一般", "促销少"]
    ad_syn = ["广告太多", "宣传浮夸", "代言不合适", "综艺植入过度"]
    lactose_syn = ["不胀气", "对肠胃友好", "乳糖不耐也能喝"]
    freshness_syn = ["更新慢", "内容滞后", "过期信息多"]
    stability_syn = ["偶发报错", "超时", "卡顿"]

    # Segment pools
    regions = ["华北", "华东", "华南", "华中", "西南", "东北"]
    cities_tier1 = ["北京", "上海", "广州", "深圳"]
    cities_tier2 = ["杭州", "南京", "成都", "武汉", "西安", "重庆"]
    cities_tier3 = ["合肥", "泉州", "石家庄", "长春", "南昌", "温州", "佛山"]
    channels = ["电商", "线下商超", "社区团购", "小程序直购"]
    ages = ["18-24", "25-34", "35-44", "45-54"]

    # Scenario presets to embed insights
    if scenario in (None, "auto"):
        scenario = "product_insight1" if survey_type == "product_nps" else "platform_insight1"

    # Time windows (first half vs second half) to simulate fixes or launches
    fix_window = count // 2

    # Simple memory to reduce exact duplicates
    seen_texts = set()

    for i in range(count):
        p = _weighted_choice(weighted_personas)
        score = _choose_scores(p["score_dist"])
        category = _categorize(score)
        start_time, submit_time, duration = _dt_range(base_dt, i)

        # Assemble factor selections
        pos_selected = _clamp_factors(p.get("pos", []), factors_pos, max_k=3)
        neg_selected = _clamp_factors(p.get("neg", []), factors_neg, max_k=3)

        # Scenario-driven adjustments to embed signals
        if survey_type == "product_nps" and scenario == "product_insight1":
            # Early packaging issue: more packaging complaints among detractors in first half
            if i < fix_window and category == "detractor":
                if any("包装设计不好" in f for f in factors_neg):
                    if "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）" in factors_neg and random.random() < 0.6:
                        if "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）" not in neg_selected:
                            neg_selected.append("包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）")
            # Price sensitivity in tier-3 cities for high-end brands
            # Applied later in text, but reinforce factor selection
            if category == "detractor" and random.random() < 0.4:
                if "产品价格太贵，性价比不高" in factors_neg and "产品价格太贵，性价比不高" not in neg_selected:
                    neg_selected.append("产品价格太贵，性价比不高")
            # Lactose-intolerant positives emphasize comfort
            if category == "promoter" and random.random() < 0.3:
                if "饮用后体感舒适，无不良反应" in factors_pos and "饮用后体感舒适，无不良反应" not in pos_selected:
                    pos_selected.append("饮用后体感舒适，无不良反应")

        if survey_type == "system_platform" and scenario == "platform_insight1":
            # New user onboarding friction increases certain negatives
            if p["name"].startswith("新同事") and category != "promoter":
                for f in ["操作复杂难上手", "功能难找"]:
                    if f in factors_neg and f not in neg_selected and random.random() < 0.7:
                        neg_selected.append(f)
            # Sales needs data helpfulness
            if p["name"].startswith("销售") and category != "promoter":
                if "数据帮助不大" in factors_neg and "数据帮助不大" not in neg_selected and random.random() < 0.6:
                    neg_selected.append("数据帮助不大")
            # Tech stability
            if p["name"].startswith("技术") and category != "promoter":
                if "性能不稳定" in factors_neg and "性能不稳定" not in neg_selected and random.random() < 0.5:
                    neg_selected.append("性能不稳定")

        # Open text based on survey_type
        if survey_type == "product_nps":
            # Build richer, varied text
            # Preference brands by persona to create patterns
            if "舒化" in (brand_names or [] ) and "乳糖不耐" in p["name"] and random.random() < 0.7:
                brand = "舒化"
            elif "金典" in (brand_names or []) and ("价格敏感" in p["name"] or random.random() < 0.3):
                brand = "金典"
            elif "安慕希" in (brand_names or []) and ("年轻白领" in p["name"] or random.random() < 0.3):
                brand = "安慕希"
            else:
                brand = random.choice(brand_names) if brand_names else "伊利"
            def gen_pos() -> str:
                t = random.choice(taste_adjs)
                sc = random.choice(scenarios)
                pk = random.choice(pack_phrases)
                base = random.choice(p.get("pos_text", [""]))
                add = ""
                if "舒化" in brand and random.random() < 0.5:
                    add = random.choice(lactose_syn)
                    add = f"，{add}"
                msg = f"{brand}喝起来{t}，{sc}来一盒刚好，包装{pk}{add}。{base}".strip()
                return msg
            def gen_neg() -> str:
                # Embed theme synonyms by scenario and index window
                if scenario == "product_insight1" and i < fix_window and random.random() < 0.6:
                    na = random.choice(packaging_syn)
                else:
                    na = random.choice(neg_adjs)
                imp = random.choice(improv_phrases)
                base = random.choice(p.get("neg_text", [""]))
                # Add price/ad synonyms sometimes
                add2 = ""
                if random.random() < 0.3:
                    add2 = random.choice(price_syn)
                elif random.random() < 0.3:
                    add2 = random.choice(ad_syn)
                add2 = f"，{add2}" if add2 else ""
                msg = f"{brand}最近{na}{add2}，{base}，希望{imp}。".replace("，，", "，").strip()
                return msg
            pos_text = gen_pos() if category == "promoter" else ""
            neg_text = gen_neg() if category == "detractor" else ""
            # Avoid exact duplicates a bit
            tries = 0
            while pos_text and pos_text in seen_texts and tries < 3:
                pos_text = gen_pos(); tries += 1
            tries = 0
            while neg_text and neg_text in seen_texts and tries < 3:
                neg_text = gen_neg(); tries += 1
            if pos_text:
                seen_texts.add(pos_text)
            if neg_text:
                seen_texts.add(neg_text)

            # Occasionally fill other_specified to enrich
            other_pos = None
            other_neg = None
            if random.random() < 0.15 and pos_selected:
                other_pos = f"{brand}联名口味好评"
            if random.random() < 0.15 and neg_selected:
                other_neg = "口味希望更清爽"

            open_responses = {
                "expectations": None,
                "suggestions": None,
                "specific_reasons": {"negative": neg_text or "", "positive": pos_text or ""},
            }
        else:
            # Platform: produce richer expectation/suggestion
            def gen_exp() -> str:
                base = random.choice(p.get("exp_text", [""]))
                # Time-based improvement after launch (second half less freshness complaints)
                extras = [
                    "支持自定义报表导出",
                    "增加按角色的操作指引",
                    "提供搜索联想与筛选",
                    "开放数据看板与订阅",
                ]
                if scenario == "platform_insight1" and i < fix_window and random.random() < 0.4:
                    extras.append("提高内容更新频率")
                extra = random.choice(extras)
                return f"{base}{('，' if base else '')}{extra}。".strip("。") + "。"
            def gen_sug() -> str:
                base = random.choice(p.get("sug_text", [""]))
                extra = random.choice([
                    "优化导航信息架构",
                    "减少重复填写的步骤",
                    "提升移动端交互细节",
                    "加强页面加载速度",
                    random.choice(stability_syn) if (scenario == "platform_insight1" and random.random() < 0.3) else "提升检索效率",
                ])
                return f"{base}{('，' if base else '')}{extra}。".strip("。") + "。"
            exp_text = gen_exp()
            sug_text = gen_sug()
            # Avoid duplicates
            if exp_text in seen_texts:
                exp_text = gen_exp()
            if sug_text in seen_texts:
                sug_text = gen_sug()
            seen_texts.update([exp_text, sug_text])
            open_responses = {
                "expectations": exp_text,
                "suggestions": sug_text,
                "specific_reasons": {"negative": None, "positive": None},
            }

        # Segment attributes for richer analysis
        if random.random() < 0.5:
            city = random.choice(cities_tier1)
            city_tier = "一线"
        elif random.random() < 0.7:
            city = random.choice(cities_tier2)
            city_tier = "二线"
        else:
            city = random.choice(cities_tier3)
            city_tier = "三线"
        region = random.choice(regions)
        channel = random.choice(channels)
        age = random.choice(ages)

        responses.append(
            {
                "response_metadata": {
                    "user_id": str(i + 1),
                    "response_id": _rand_id(8),
                    "response_type": "正式",
                    "distribution_method": "链接二维码",
                    "status": "已完成",
                    "timing": {
                        "start_time": start_time,
                        "submit_time": submit_time,
                        "duration": duration,
                    },
                    "annotation": {
                        "ai_status": "未标记",
                        "ai_reason": "",
                        "manual_status": "未标记",
                        "manual_reason": "",
                    },
                    "persona": p["name"],
                    "region": region,
                    "city": city,
                    "city_tier": city_tier,
                    "channel": channel,
                    "age_group": age,
                },
                "nps_score": {
                    "value": score,
                    "raw_value": f"{score}分",
                    "category": category,
                },
                "factor_responses": {
                    "negative_factors": {"selected": neg_selected, "other_specified": other_neg if survey_type == "product_nps" else None},
                    "positive_factors": {"selected": pos_selected, "other_specified": other_pos if survey_type == "product_nps" else None},
                },
                "open_responses": open_responses,
            }
        )

    # Replace response_data
    sr["response_data"] = responses
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", type=str, default="auto", help="auto|product_insight1|platform_insight1|none")
    args = parser.parse_args()

    random.seed(args.seed)

    with open(args.input, "r", encoding="utf-8") as f:
        doc = json.load(f)

    out_doc = generate_responses(doc, args.count, scenario=args.scenario)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
