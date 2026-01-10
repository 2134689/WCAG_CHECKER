import re
from typing import Tuple, Optional


def parse_rgb(rgb_string: str) -> Optional[Tuple[int, int, int]]:
    if not rgb_string:
        return None
    nums = re.findall(r"\d+", rgb_string)
    if len(nums) < 3:
        return None
    return int(nums[0]), int(nums[1]), int(nums[2])


def luminance(rgb: Tuple[int, int, int]) -> float:
    def channel(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg, bg) -> float:
    l1 = luminance(fg)
    l2 = luminance(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def is_large_text(font_size: str) -> bool:
    try:
        return float(font_size.replace("px", "")) >= 18
    except Exception:
        return False


def wcag_level(ratio, large=False):
    if large:
        if ratio >= 4.5:
            return "AAA"
        if ratio >= 3:
            return "AA"
        return "Fail"
    else:
        if ratio >= 7:
            return "AAA"
        if ratio >= 4.5:
            return "AA"
        return "Fail"


def star_rating(pass_ratio: float) -> int:
    if pass_ratio >= 0.95:
        return 5
    if pass_ratio >= 0.85:
        return 4
    if pass_ratio >= 0.70:
        return 3
    if pass_ratio >= 0.50:
        return 2
    return 1


def suggest_wcag_color(bg_rgb, min_ratio=4.5):
    for i in range(256):
        candidate = (i, i, i)
        if contrast_ratio(candidate, bg_rgb) >= min_ratio:
            return candidate
    return (0, 0, 0)


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)
