import json, sys
from PIL import Image, ImageDraw, ImageFont
S = 6  # pixels per unit
COL = {"navy":"#0f172a","slate":"#475569","steel":"#64748b","cyan":"#22d3ee","sky":"#38bdf8",
 "amber":"#f59e0b","gold":"#fbbf24","coral":"#fb5f6f","orange":"#f97316","white":"#ffffff",
 "dark":"#0b1220","skin":"#f1c6a0","hair":"#3a2a20","main":"#3b82f6","main2":"#1e3a8a"}
def rgb(n):
    h = COL.get(n, "#ff00ff").lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def render(asset, bg=(30,41,59)):
    W, H = asset["w"], asset["h"]; k = 2
    base = Image.new("RGBA", (W*S*k, H*S*k), bg+(255,))
    for s in asset["shapes"]:
        ov = Image.new("RGBA", base.size, (0,0,0,0)); d = ImageDraw.Draw(ov)
        c = rgb(s["c"]) + (int(255*s.get("a",1)),); f = S*k; t = s["t"]
        if t=="rect": d.rectangle([s["x"]*f,s["y"]*f,(s["x"]+s["w"])*f,(s["y"]+s["h"])*f], fill=c)
        elif t=="rrect": d.rounded_rectangle([s["x"]*f,s["y"]*f,(s["x"]+s["w"])*f,(s["y"]+s["h"])*f], radius=s.get("r",2)*f, fill=c)
        elif t=="circle": d.ellipse([(s["cx"]-s["r"])*f,(s["cy"]-s["r"])*f,(s["cx"]+s["r"])*f,(s["cy"]+s["r"])*f], fill=c)
        elif t=="ellipse": d.ellipse([(s["cx"]-s["rx"])*f,(s["cy"]-s["ry"])*f,(s["cx"]+s["rx"])*f,(s["cy"]+s["ry"])*f], fill=c)
        elif t=="ring":
            r,w=s["r"],s["w"]; d.ellipse([(s["cx"]-r)*f,(s["cy"]-r)*f,(s["cx"]+r)*f,(s["cy"]+r)*f], outline=c, width=int(w*f))
        elif t=="poly": d.polygon([(x*f,y*f) for x,y in s["pts"]], fill=c)
        elif t=="line":
            d.line([s["x1"]*f,s["y1"]*f,s["x2"]*f,s["y2"]*f], fill=c, width=max(1,int(s["w"]*f)))
            r=s["w"]*f/2
            for x,y in ((s["x1"],s["y1"]),(s["x2"],s["y2"])): d.ellipse([x*f-r,y*f-r,x*f+r,y*f+r], fill=c)
        base = Image.alpha_composite(base, ov)
    return base.resize((W*S, H*S), Image.LANCZOS)
data = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2] if len(sys.argv)>2 else "preview.png"
cols = 4; pad = 20; items = list(data.items())
ims = [render(a) for _,a in items]
cw = max(i.width for i in ims)+pad; ch = max(i.height for i in ims)+pad+24
rows = (len(ims)+cols-1)//cols
sheet = Image.new("RGB", (cols*cw, rows*ch), (15,23,42)); dr = ImageDraw.Draw(sheet)
for n,(im,(name,_)) in enumerate(zip(ims,items)):
    x=(n%cols)*cw+pad//2; y=(n//cols)*ch+pad//2
    sheet.paste(im,(x,y),im); dr.text((x,y+im.height+4), name, fill=(230,230,230))
sheet.save(out); print("saved", out)
