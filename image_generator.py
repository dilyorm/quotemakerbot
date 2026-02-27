import os
import urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import hashlib
import textwrap
from typing import Optional

def download_font() -> tuple[str, str]:
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", font_bold)
        
    return font_reg, font_bold

def get_name_color(name: str) -> str:
    colors = [
        "#fb6169", "#85bda7", "#fca460", "#5ca0cc",
        "#b388d0", "#50a793", "#e8718f"
    ]
    hash_val = int(hashlib.md5(name.encode('utf-8')).hexdigest(), 16)
    return colors[hash_val % len(colors)]

def make_circle(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    
    result = Image.new('RGBA', size, (0, 0, 0, 0))
    result.paste(image, (0, 0), mask=mask)
    return result

def get_wrapped_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    paragraphs = text.split('\n')
    for p in paragraphs:
        if not p.strip():
            lines.append("")
            continue
        words = p.split(' ')
        current_line = words[0]
        for word in words[1:]:
            bbox = font.getbbox(current_line + " " + word)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

def create_quote_image(avatar_bytes: Optional[bytes], name: str, text: str, theme: str = "default") -> BytesIO:
    reg_font_path, bold_font_path = download_font()
    
    font_size_text = 28
    font_size_name = 28
    font_size_time = 20
    
    try:
        font_text = ImageFont.truetype(reg_font_path, font_size_text)
        font_name = ImageFont.truetype(bold_font_path, font_size_name)
        font_time = ImageFont.truetype(reg_font_path, font_size_time)
    except IOError:
        font_text = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_time = ImageFont.load_default()

    avatar_size = (80, 80)
    
    themes_dict = {
        "sigma": {"bg": "#0a0a0a", "bubble": "#222222", "text": "#ffffff", "time": "#888888", "avatar_bg": "#444444"},
        "hacker": {"bg": "#000000", "bubble": "#002200", "text": "#00ff00", "time": "#008800", "avatar_bg": "#004400"},
        "romantic": {"bg": "#ffe6ea", "bubble": "#ff88a7", "text": "#ffffff", "time": "#ffe6ea", "avatar_bg": "#ff3366"},
        "hustle": {"bg": "#1a1600", "bubble": "#4d4000", "text": "#ffd700", "time": "#ccaa00", "avatar_bg": "#ffae00"},
        "spooky": {"bg": "#0a0000", "bubble": "#330000", "text": "#ff8888", "time": "#cc0000", "avatar_bg": "#550000"},
        "sad": {"bg": "#1c2841", "bubble": "#2d3e5e", "text": "#aabde6", "time": "#6a81b3", "avatar_bg": "#151e33"}
    }
    
    if theme in themes_dict:
        bg_color = themes_dict[theme]["bg"]
        bubble_color = themes_dict[theme]["bubble"]
        text_color = themes_dict[theme]["text"]
        time_color = themes_dict[theme]["time"]
        avatar_bg_color = themes_dict[theme]["avatar_bg"]
    else:
        bg_color = "#0e1621"
        bubble_color = "#182533"
        text_color = "#ffffff"
        time_color = "#6e7f8d"
        avatar_bg_color = get_name_color(name)
        
    avatar = None
    
    if avatar_bytes:
        try:
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGB")
        except Exception:
            avatar = None
            
    if not avatar_bytes or avatar is None:
        avatar = Image.new("RGB", avatar_size, avatar_bg_color)
        draw_temp = ImageDraw.Draw(avatar)
        try:
            temp_font = ImageFont.truetype(bold_font_path, 40)
        except Exception:
            temp_font = font_name
            
        letter = name[0].upper() if name else "?"
        bbox = draw_temp.textbbox((0, 0), letter, font=temp_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw_temp.text(((avatar_size[0] - w) / 2, (avatar_size[1] - h) / 2 - 8), letter, font=temp_font, fill="white")
        
    avatar = make_circle(avatar, avatar_size)
    
    max_text_width = 800
    lines = get_wrapped_lines(text, font_text, max_text_width)
    
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    name_bbox = temp_draw.textbbox((0, 0), name, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    name_height = name_bbox[3] - name_bbox[1]
    
    line_bboxes = [temp_draw.textbbox((0, 0), line if line else "A", font=font_text) for line in lines]
    text_width = max([bbox[2] - bbox[0] for bbox in line_bboxes] + [0])
    
    avg_line_height = font_size_text + 6
    total_text_height = sum([avg_line_height if line else avg_line_height // 2 for line in lines])
    
    time_text = datetime.now().strftime("%H:%M")
    time_bbox = temp_draw.textbbox((0, 0), time_text, font=font_time)
    time_width = time_bbox[2] - time_bbox[0]
    time_height = time_bbox[3] - time_bbox[1]
    
    bubble_padding_h = 24
    bubble_padding_v = 16
    
    bubble_content_width = max(name_width, text_width)
    bubble_width = bubble_content_width + bubble_padding_h * 2
    
    last_line = lines[-1] if lines else ""
    last_line_bbox = temp_draw.textbbox((0, 0), last_line, font=font_text)
    last_line_width = last_line_bbox[2] - last_line_bbox[0]
    
    if bubble_content_width - last_line_width > time_width + 16:
        pass
    else:
        total_text_height += font_size_time
        bubble_width = max(bubble_width, last_line_width + time_width + bubble_padding_h * 2 + 16)
        
    bubble_width = max(bubble_width, name_width + bubble_padding_h * 2)
    bubble_height = bubble_padding_v + name_height + 10 + total_text_height + bubble_padding_v
    
    padding_bg_h = 40
    padding_bg_v = 40
    img_width = padding_bg_h + avatar_size[0] + 16 + bubble_width + padding_bg_h + 80
    img_height = padding_bg_v + max(avatar_size[1], bubble_height) + padding_bg_v
    
    img = Image.new("RGBA", (int(img_width), int(img_height)), bg_color)
    draw = ImageDraw.Draw(img)
    
    avatar_x = padding_bg_h
    avatar_y = img_height - padding_bg_v - avatar_size[1]
    img.paste(avatar, (avatar_x, int(avatar_y)), avatar)
    
    bubble_x = avatar_x + avatar_size[0] + 16
    bubble_y = img_height - padding_bg_v - bubble_height
    
    bubble_radius = 24
    draw.rounded_rectangle([bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height], radius=bubble_radius, fill=bubble_color)
    
    tail_polygon = [
        (bubble_x, img_height - padding_bg_v - 20),
        (bubble_x - 12, img_height - padding_bg_v),
        (bubble_x + 24, img_height - padding_bg_v)
    ]
    draw.polygon(tail_polygon, fill=bubble_color)
    
    text_x = bubble_x + bubble_padding_h
    current_y = bubble_y + bubble_padding_v - 4
    
    draw.text((text_x, current_y), name, font=font_name, fill=avatar_bg_color)
    current_y += name_height + 14
    
    for line in lines:
        if line:
            draw.text((text_x, current_y), line, font=font_text, fill=text_color)
            current_y += avg_line_height
        else:
            current_y += avg_line_height // 2
            
    time_x = bubble_x + bubble_width - bubble_padding_h - time_width
    time_y = bubble_y + bubble_height - bubble_padding_v - time_height + 6
    draw.text((time_x, time_y), time_text, font=font_time, fill=time_color)
    
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output
