"""Run once in repo root: python patch_script_gen2.py  (keeps script_gen2.py.bak)"""
import shutil
src = open("script_gen2.py", encoding="utf-8").read()
shutil.copy("script_gen2.py", "script_gen2.py.bak")
a = src.index("SCENE DRAWING (our own code")
b = src.index('"""\n\n\n# ---------- subjects')
NEW = '''SCENE DRAWING (our own code draws it, you only describe it)
background: navy, slate, teal, dusk, void (use a "sky" element on top of it when you want a sky).
camera: push, pull, static.
Each scene has 6 to 14 elements. x and y are the CENTRE of the element. x is percent of the screen width
(0 left, 100 right). y is percent of the picture area (0 top, 100 bottom of the picture area). Captions have
their own space at the bottom, so you cannot cover them. Sizes s and h are percent of the screen width.
Colour names: navy, slate, gray, cyan, mint, amber, red, white, cream, dark, purple, brown, blue.

SCENERY (draw these first, in this order: sky, far objects, ground or sea, near objects):
- sky: style (day, dusk, night, storm, red, space). No x, y, s. Always the first element.
- mountain, sun, moon, earth, cloud, tree: x, y, s, optional color. (sun s 15 to 30, earth s 20 to 45)
- city: x, y, s. y is the ground line, s is the height of the tallest building (20 to 50).
- ground: style (grass, desert, rock, snow, lava, dark), x 50, y, s 100. y is the surface line, it fills down.
- sea: style (water, lava, ice), x 50, y, s 100. y is the water line, it fills down.
- crowd: x, y, s (width, 50 to 90), n (3 to 20 people), h (7 to 12, person height), bob (0 to 3).
- skyline, window (view: stars, city, planet, ocean), planet (ring true/false), pod, rect, clock: as before
  (x, y, s, color).

CHARACTER:
- figure: x, y, s (40 to 55: the figure must be BIG), body (colour), head (use gray), eyes (open, closed,
  wide), pose (stand, lie), arm_up (true/false), angle (degrees). The main character is "you".

SYMBOLS AND TEXT:
- icon: icon (drop, flame, bolt, thermometer, house, heart, warning, hourglass), x, y, s (10 to 20), color.
  Use icons to show what the narration talks about (heat = thermometer or flame, danger = warning, home = house).
- arrow: x, y, s (15 to 35), angle (degrees, 0 = right, -90 = up), color.
- badge: x, y, text (UPPERCASE, max 24 characters, ideally 1 to 4 words), color. For dates and labels,
  like "DAY 3", "800 MPH", "35,000 FT".
- text: x, y, text (max 24 characters), color.
- timer: no x and y (it is locked in the top-right corner). at, from. A digital counter that counts up.
  "from" is the number of seconds it shows when it appears. Use it only when seconds or minutes matter,
  and continue the count from the previous scene.
- particles: kind (rain, snow, embers). No x, y, s. Weather or fire in the air. Add it after the objects.
- disc: x, y, s, color. Only for a ball or a light, never as decoration.

Optional fields for any element: at (seconds when it appears), until (seconds when it disappears),
move_to [x, y] with move_at and move_time (seconds), shake (0 to 5), bob (0 to 5), pop (false turns
the pop-in off).

Rules for drawing:
- Every scene is a full picture: a sky or background, scenery (ground, sea, city, mountain...), the figure,
  and at least one icon, arrow or badge that shows the point of the sentence. Never a figure with two plain
  circles. Never a big empty area.
- Every scene must be different from the one before it. Change the sky, the scenery, the camera, the
  objects or the layout. Never reuse the same scene twice in a row.
- Place the figure standing on the ground or sea line when there is one. Keep it between x 25 and 75.
- Show the place and the danger of the narration with scenery and icons (a flooded city = city + sea +
  warning icon), not with abstract shapes.
- Use a badge for every number or date mentioned in the narration.
- Only use the types, colours and values listed here. Anything else makes the scene unusable.
- Time values are in seconds and must stay between 0 and 6.
'''
src = src[:a] + NEW + src[b:]
src = src.replace("1 to 16 elements", "6 to 14 elements")
open("script_gen2.py", "w", encoding="utf-8").write(src)
print("script_gen2.py patched")
