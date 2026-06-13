from PIL import Image, ImageDraw, ImageFilter
import math

def draw_ai_prompt_icon(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ===== ФОН =====
    bg = Image.new("RGBA", (size, size))

    for y in range(size):
        ratio = y / size

        r = int(10 + ratio * 30)
        g = int(15 + ratio * 25)
        b = int(40 + ratio * 80)

        for x in range(size):
            bg.putpixel((x, y), (r, g, b, 255))

    img.alpha_composite(bg)

    draw = ImageDraw.Draw(img)

    # ===== СКРУГЛЕННЫЙ КВАДРАТ =====
    margin = size // 16

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 5,
        fill=255
    )

    rounded = Image.new("RGBA", (size, size))
    rounded.paste(img, (0, 0), mask)

    img = rounded

    # ===== НЕОНОВОЕ СВЕЧЕНИЕ =====
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    cx = size // 2
    cy = size // 2

    glow_radius = size // 4

    glow_draw.ellipse(
        [
            cx - glow_radius,
            cy - glow_radius,
            cx + glow_radius,
            cy + glow_radius
        ],
        fill=(0, 255, 255, 120)
    )

    glow_layer = glow_layer.filter(
        ImageFilter.GaussianBlur(radius=size // 20)
    )

    img.alpha_composite(glow_layer)

    draw = ImageDraw.Draw(img)

    # ===== ШЕСТИГРАННИК AI =====
    r = size * 0.18

    points = []

    for i in range(6):
        angle = math.radians(60 * i - 30)

        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)

        points.append((x, y))

    draw.polygon(
        points,
        outline=(0, 255, 255),
        width=max(4, size // 64)
    )

    # ===== ВНУТРЕННИЕ ЛИНИИ =====
    for p in points:
        draw.line(
            [(cx, cy), p],
            fill=(0, 255, 255),
            width=max(2, size // 128)
        )

    # ===== ИСКРЫ УЛУЧШЕНИЯ ПРОМПТА =====
    spark_color = (255, 255, 255)

    spark_size = size // 18

    positions = [
        (cx - size // 4, cy - size // 4),
        (cx + size // 4, cy - size // 5),
        (cx + size // 5, cy + size // 4),
    ]

    for sx, sy in positions:
        draw.line(
            [(sx, sy - spark_size), (sx, sy + spark_size)],
            fill=spark_color,
            width=3
        )

        draw.line(
            [(sx - spark_size, sy), (sx + spark_size, sy)],
            fill=spark_color,
            width=3
        )

    return img


# ===== СОХРАНЕНИЕ ICO =====

icon = draw_ai_prompt_icon(512)

sizes = [
    (256, 256),
    (128, 128),
    (64, 64),
    (48, 48),
    (32, 32),
    (16, 16)
]

icon.save(
    "app.ico",
    format="ICO",
    sizes=sizes
)

print("✅ Создана современная AI-иконка app.ico")