import json
import re


LANGUAGE_OPTIONS = (
    "中文",
    "英语",
    "德语",
    "法语",
    "日语",
    "韩语",
    "葡萄牙语",
)

ASPECT_RATIO_OPTIONS = ("1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16")

USAGE_OPTIONS = ("主图", "主图+详情页", "详情页", "海报", "种草图", "其它")

PAGE_CONTENT_OPTIONS = ("精简", "中等", "丰富")

FONT_STYLE_OPTIONS = (
    "自动判断",
    "现代极简无衬线字体",
    "人文温柔无衬线字体",
    "高级时尚衬线字体",
    "东方雅致宋体字体",
    "新中式书法展示字体",
    "圆润亲和字体",
    "潮流个性展示字体",
    "几何科技字体",
    "自然手作字体",
    "奢华品牌字体",
    "复古艺术字体",
)

REVERSE_PAGE_OPTIONS = ("自动判断", "不插入", "插入1张", "插入2张", "插入3张")

MODEL_SETTING_OPTIONS = ("自动判断", "不使用模特", "女性模特", "男性模特")

MODEL_APPEARANCE_OPTIONS = ("自动判断",) + tuple(str(value) for value in range(1, 26))

PAGE_CONTENT_DIRECTIVES = {
    "精简": (
        "每张图片只保留一个核心视觉主体和最多一个必要辅助信息组；"
        "消费者可见文案以主标题加至多一条辅助文案为上限。"
    ),
    "中等": (
        "每张图片使用一个核心视觉主体和一至两个辅助信息组；"
        "保留清晰的主标题、副标题和一个事实点，避免堆叠重复模块。"
    ),
    "丰富": (
        "在商品事实充分时，每张图片可使用一个核心视觉主体和二至四个辅助信息组；"
        "不得为了填满画面虚构数据、模块或重复同一内容。"
    ),
}


def _clean_text(value):
    return str(value or "").strip()


def _maximum_reverse_pages(quantity):
    # 参考一键电商的版式约束：反转页最多占总页数的四分之一，且不超过三张。
    return min(3, max(0, int(quantity)) // 4)


def _recommended_reverse_pages(quantity):
    quantity = max(0, int(quantity))
    if quantity < 5:
        recommended = 0
    elif quantity < 10:
        recommended = 1
    elif quantity < 16:
        recommended = 2
    else:
        recommended = 3
    return min(recommended, _maximum_reverse_pages(quantity))


def _normalize_reverse_pages(value, quantity, usage):
    maximum = _maximum_reverse_pages(quantity)
    if "详情页" not in usage:
        return "manual", 0, "不插入", maximum
    if value == "自动判断":
        return "auto", _recommended_reverse_pages(quantity), "自动判断", maximum

    match = re.search(r"\d+", _clean_text(value))
    requested = int(match.group(0)) if match else 0
    count = min(requested, maximum)
    label = "不插入" if count == 0 else f"插入{count}张"
    return "manual", count, label, maximum


def _normalize_model_appearance(value, quantity, model_setting):
    if model_setting == "不使用模特":
        return 0, "不使用模特"
    if value == "自动判断":
        return None, "自动判断"

    try:
        count = int(value)
    except (TypeError, ValueError):
        return None, "自动判断"
    count = min(max(1, count), max(1, int(quantity)))
    return count, str(count)


class MengBaoEcommerceSettings:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "product_name": (
                    "STRING",
                    {"default": "", "placeholder": "请输入产品名称"},
                ),
                "copy_information": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "请输入商品卖点、成分、参数或已有文案",
                    },
                ),
                "special_requirements": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "请输入人物特征、场景、禁用元素等特殊要求",
                    },
                ),
                "product_size": (
                    "STRING",
                    {"default": "", "placeholder": "例如：长 12cm × 宽 4cm × 高 4cm"},
                ),
                "language": (list(LANGUAGE_OPTIONS), {"default": "中文"}),
                "quantity": (
                    "INT",
                    {"default": 8, "min": 1, "max": 25, "step": 1},
                ),
                "aspect_ratio": (
                    list(ASPECT_RATIO_OPTIONS),
                    {"default": "9:16"},
                ),
                "usage": (list(USAGE_OPTIONS), {"default": "详情页"}),
                "page_content": (
                    list(PAGE_CONTENT_OPTIONS),
                    {"default": "中等"},
                ),
                "font_style": (
                    list(FONT_STYLE_OPTIONS),
                    {"default": "自动判断"},
                ),
                "reverse_pages": (
                    list(REVERSE_PAGE_OPTIONS),
                    {"default": "自动判断"},
                ),
                "model_setting": (
                    list(MODEL_SETTING_OPTIONS),
                    {"default": "自动判断"},
                ),
                "model_appearance_count": (
                    list(MODEL_APPEARANCE_OPTIONS),
                    {"default": "自动判断"},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("user_prompt", "aspect_ratio", "quantity", "settings_json")
    FUNCTION = "build"
    CATEGORY = "萌宝AI/电商"
    DESCRIPTION = "集中配置产品信息与电商图片参数，输出可复用的提示词和 JSON 设置。"
    SEARCH_ALIASES = [
        "Meng",
        "MengBao",
        "MengBaoAI",
        "MengBao AI",
        "MengBaoEcommerceSettings",
        "MengBao AI Ecommerce Settings",
        "MengBao AI E-commerce Settings",
        "萌宝",
        "萌宝AI",
        "萌宝AI 电商设置",
        "MengBao AI电商设置",
        "一键电商",
        "电商设置",
    ]

    def build(
        self,
        product_name,
        copy_information,
        special_requirements,
        product_size,
        language,
        quantity,
        aspect_ratio,
        usage,
        page_content,
        font_style,
        reverse_pages,
        model_setting,
        model_appearance_count,
    ):
        quantity = min(25, max(1, int(quantity)))
        product_name = _clean_text(product_name)
        copy_information = _clean_text(copy_information)
        special_requirements = _clean_text(special_requirements)
        product_size = _clean_text(product_size)

        reverse_mode, reverse_count, reverse_label, reverse_maximum = (
            _normalize_reverse_pages(reverse_pages, quantity, usage)
        )
        model_count, model_count_label = _normalize_model_appearance(
            model_appearance_count,
            quantity,
            model_setting,
        )

        settings = {
            "product_name": product_name,
            "copy_information": copy_information,
            "special_requirements": special_requirements,
            "product_size": product_size,
            "language": language,
            "quantity": quantity,
            "aspect_ratio": aspect_ratio,
            "usage": usage,
            "page_content": page_content,
            "font_style": font_style,
            "reverse_pages": reverse_label,
            "reverse_page_mode": reverse_mode,
            "reverse_page_count": reverse_count,
            "reverse_page_maximum": reverse_maximum,
            "model_setting": model_setting,
            "model_appearance": model_count_label,
            "model_appearance_count": model_count,
        }

        # 未提供的商品事实保持为空，提示词明确禁止模型自行补写功效和尺寸。
        copy_text = copy_information or "未提供；只能使用可确认的商品事实，不得补写未经核验的功效或参数。"
        requirement_text = special_requirements or "无额外要求。"
        size_text = product_size or "未提供；不得根据照片像素或留白猜测真实产品尺寸。"
        content_directive = PAGE_CONTENT_DIRECTIVES.get(
            page_content,
            PAGE_CONTENT_DIRECTIVES["中等"],
        )

        if reverse_mode == "auto":
            reverse_directive = (
                f"由内容策划在 0 至 {reverse_maximum} 张范围内决定反转页的数量、位置和强度。"
            )
        else:
            reverse_directive = f"严格使用 {reverse_count} 张反转页。"

        if model_setting == "不使用模特":
            model_directive = "全部页面禁止出现模特。"
        elif model_count is None:
            model_directive = f"模特设置为“{model_setting}”，由内容策划判断出现次数。"
        else:
            model_directive = f"模特设置为“{model_setting}”，必须恰好在 {model_count} 张图片中出现。"

        prompt = "\n".join(
            [
                "请根据以下设置策划并生成一套完整、统一的电商视觉图片。",
                f"产品名称：{product_name or '未填写'}",
                f"文案信息：{copy_text}",
                f"特殊要求：{requirement_text}",
                f"产品尺寸：{size_text}",
                f"输出语言：{language}",
                f"用途：{usage}",
                f"图片比例：{aspect_ratio}",
                f"页面内容：{page_content}。{content_directive}",
                f"字体风格：{font_style}",
                f"插入反转页：{reverse_label}。{reverse_directive}",
                f"模特设置：{model_setting}；模特出现率：{model_count_label}。{model_directive}",
                f"必须严格生成 {quantity} 张，保持产品外观、结构比例、品牌与包装文字一致。",
                "所有卖点、参数、认证、检测数据、材质、销量、时效与使用效果只能来自用户提供的信息或可核验事实，不得虚构。",
            ]
        )

        return (
            prompt,
            aspect_ratio,
            quantity,
            json.dumps(settings, ensure_ascii=False, indent=2),
        )
