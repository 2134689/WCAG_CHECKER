import re
from typing import Tuple, Optional, Union

def parse_rgb(color_string: str) -> Optional[Tuple[int, int, int]]:
    if not color_string: return None
    if color_string.startswith('#'):
        hex_val = color_string.lstrip('#')
        if len(hex_val) == 3: hex_val = ''.join([c*2 for c in hex_val])
        try: return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
        except: return None
    nums = re.findall(r"\d+", color_string)
    if len(nums) < 3: return None
    return int(nums[0]), int(nums[1]), int(nums[2])

def luminance(rgb: Tuple[int, int, int]) -> float:
    def channel(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def contrast_ratio(fg: Tuple[int, int, int], bg: Tuple[int, int, int]) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def star_rating(pass_ratio: float) -> int:
    if pass_ratio >= 0.95: return 5
    if pass_ratio >= 0.85: return 4
    if pass_ratio >= 0.70: return 3
    if pass_ratio >= 0.50: return 2
    return 1

def suggest_wcag_color(bg_rgb: Tuple[int, int, int], target_ratio: float = 4.5) -> Tuple[int, int, int]:
    if contrast_ratio((0, 0, 0), bg_rgb) >= target_ratio: return (0, 0, 0)
    return (255, 255, 255)

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)
