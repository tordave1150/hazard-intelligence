"""
3D Hero Section — Canvas 2D particle sphere animation.

Task 1: Renders an animated particle sphere hero that works within
Streamlit's iframe sandbox (no WebGL/Three.js, uses Canvas 2D API).

Redesigned to match the open-design/design-systems/dashboard aesthetic:
- Dark navy panel background (#0c1220 → #0f1e35)
- Sky-blue (#0ea5e9) primary particles + teal secondary
- Raised panel shadow (0 18px 46px rgba(15,23,42,.35))
- Dashboard glass-panel border (1px solid rgba(14,165,233,0.18))
- IBM Plex Mono eyebrow label for date/live indicator
- Green live-status pulse dot (top-right)

Usage:
    from components.hero_3d import render_hero_3d
    st.markdown(render_hero_3d(...), unsafe_allow_html=True)
"""


def render_hero_3d(rain_prob_avg: float, high_rain_count: int, date_str: str) -> str:
    """Return HTML string containing a Canvas-based 3D particle sphere hero.

    Args:
        rain_prob_avg:   Average rain probability — controls particle colors
                         (low = sky-blue/teal, moderate = amber/purple, high = red/orange).
        high_rain_count: Number of locations with >= 40% rain probability.
        date_str:        Selected date string for display.

    Returns:
        HTML string safe for st.markdown(..., unsafe_allow_html=True).
    """
    # Particle color scheme based on rain severity
    if rain_prob_avg < 40:
        color_a = "14,165,233"    # sky-blue (#0ea5e9) — accent
        color_b = "20,184,166"    # teal
        mood = "Low risk"
        mood_bg = "rgba(16, 185, 129, 0.12)"
        mood_border = "rgba(16, 185, 129, 0.28)"
        mood_color = "#10b981"
    elif rain_prob_avg < 70:
        color_a = "14,165,233"    # sky-blue
        color_b = "245,158,11"    # amber
        mood = "Moderate risk"
        mood_bg = "rgba(245, 158, 11, 0.12)"
        mood_border = "rgba(245, 158, 11, 0.28)"
        mood_color = "#f59e0b"
    else:
        color_a = "239,68,68"     # red
        color_b = "251,146,60"    # orange
        mood = "High risk"
        mood_bg = "rgba(239, 68, 68, 0.12)"
        mood_border = "rgba(239, 68, 68, 0.28)"
        mood_color = "#ef4444"

    return f"""
    <div id="wa-hero" style="
        position:relative;
        height:280px;
        background:linear-gradient(135deg,#0c1220 0%,#0f1e35 55%,#0a1628 100%);
        border-radius:18px;
        overflow:hidden;
        margin-bottom:16px;
        border:1px solid rgba(14,165,233,0.18);
        box-shadow: 0 18px 46px rgba(15,23,42,0.35), 0 0 0 1px rgba(14,165,233,0.10);
    ">
      <canvas id="wa-canvas" style="position:absolute;inset:0;width:100%;height:100%"></canvas>

      <!-- Subtle grid overlay -->
      <div style="position:absolute;inset:0;
          background-image:
            linear-gradient(rgba(14,165,233,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(14,165,233,0.04) 1px, transparent 1px);
          background-size: 44px 44px;
          pointer-events:none;z-index:1"></div>

      <!-- Left text overlay -->
      <div style="position:absolute;left:28px;top:50%;transform:translateY(-50%);z-index:5;pointer-events:none">
        <!-- Eyebrow: IBM Plex Mono, accent, uppercase -->
        <div style="font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;
                    color:#0ea5e9;margin-bottom:10px;
                    font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
                    display:flex;align-items:center;gap:7px;">
          <span style="width:7px;height:7px;border-radius:9999px;background:#10b981;
                       display:inline-block;animation:pulse-dot 2s infinite;"></span>
          LIVE • {date_str}
        </div>
        <div style="font-size:28px;font-weight:700;color:#f9fafb;line-height:1.1;max-width:240px;
                    font-family:'Inter',system-ui,sans-serif;letter-spacing:-0.015em">
          Thailand<br>Weather<br>Forecast
        </div>
        <div style="display:inline-flex;align-items:center;gap:6px;
                    background:{mood_bg};border:1px solid {mood_border};
                    border-radius:9999px;padding:5px 13px;font-size:11px;color:{mood_color};margin-top:14px;
                    font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-weight:700;
                    letter-spacing:0.06em;">
          {high_rain_count} points ≥40% chance · Avg {rain_prob_avg:.0f}% prob
        </div>
      </div>

      <!-- Status pill: top-right -->
      <div style="position:absolute;top:16px;right:16px;z-index:5;
                  display:inline-flex;align-items:center;gap:7px;
                  background:{mood_bg};border:1px solid {mood_border};
                  border-radius:9999px;padding:5px 13px;
                  font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;
                  font-size:10px;font-weight:700;color:{mood_color};
                  text-transform:uppercase;letter-spacing:0.10em;">
        {mood}
      </div>

      <!-- Radial glow behind sphere -->
      <div style="position:absolute;top:50%;right:20%;transform:translate(50%,-50%);
                  width:220px;height:220px;
                  background:radial-gradient(circle,rgba({color_a},0.14) 0%,transparent 70%);
                  pointer-events:none;z-index:0"></div>

      <!-- Corner accent line -->
      <div style="position:absolute;bottom:0;left:0;right:0;height:2px;
                  background:linear-gradient(90deg,transparent,rgba(14,165,233,0.5),transparent);
                  z-index:6;pointer-events:none"></div>
    </div>

    <style>
    @keyframes pulse-dot {{
        0%, 100% {{ opacity:1; transform:scale(1); }}
        50%       {{ opacity:0.55; transform:scale(0.8); }}
    }}
    </style>

    <script>
    (function(){{
      const canvas = document.getElementById('wa-canvas');
      const hero   = document.getElementById('wa-hero');
      if(!canvas || !hero) return;
      const ctx = canvas.getContext('2d');
      if(!ctx) return;
      const CA  = '{color_a}';
      const CB  = '{color_b}';
      const N   = 300;

      function resize(){{
        canvas.width  = hero.offsetWidth  || 800;
        canvas.height = hero.offsetHeight || 280;
      }}
      resize();

      const W  = () => canvas.width;
      const H  = () => canvas.height;
      const CX = () => W() * 0.72;
      const CY = () => H() * 0.5;

      // Build fibonacci sphere distribution
      const particles = [];
      for(let i = 0; i < N; i++){{
        const phi   = Math.acos(1 - 2*(i+0.5)/N);
        const theta = Math.PI*(1+Math.sqrt(5))*i;
        const r = 98;
        particles.push({{
          ox: Math.sin(phi)*Math.cos(theta)*r,
          oy: Math.sin(phi)*Math.sin(theta)*r,
          oz: Math.cos(phi)*r,
          trail: [],
          size:  1.1 + Math.random()*1.7,
          phase: Math.random()*Math.PI*2,
          color: Math.random() > 0.45 ? CA : CB
        }});
      }}

      let t = 0;
      let mx = CX(), my = CY();

      hero.addEventListener('mousemove', e => {{
        const r = canvas.getBoundingClientRect();
        mx = e.clientX - r.left;
        my = e.clientY - r.top;
      }});

      hero.addEventListener('mouseleave', () => {{
        mx = CX();
        my = CY();
      }});

      function frame(){{
        ctx.clearRect(0, 0, W(), H());
        t += 0.007;

        const tiltX = (my - CY()) * 0.0014;
        const tiltY = (mx - CX()) * 0.001 + t * 0.45;
        const cX = Math.cos(tiltX), sX = Math.sin(tiltX);
        const cY = Math.cos(tiltY), sY = Math.sin(tiltY);
        const fov = 300;

        const proj = particles.map(p => {{
          // Breathing effect
          const b  = 1 + 0.05 * Math.sin(t * 1.1 + p.phase);
          const bx = p.ox * b, by = p.oy * b, bz = p.oz * b;

          // Y-axis rotation
          const x1 =  bx * cY + bz * sY;
          const z1 = -bx * sY + bz * cY;

          // X-axis rotation
          const y2 = by * cX - z1 * sX;
          const z2 = by * sX + z1 * cX;

          // Perspective projection
          const dz = fov + z2;
          const px = CX() + x1 * fov / dz;
          const py = CY() + y2 * fov / dz;
          const sc = fov / dz;

          // Mouse repulsion
          const dx = px - mx, dy = py - my;
          const d2 = dx * dx + dy * dy;
          let rpx = px, rpy = py;
          if(d2 < 2500){{
            const d = Math.sqrt(d2) || 1;
            const f = (50 - d) * 0.2;
            rpx += dx / d * f;
            rpy += dy / d * f;
          }}

          // Trail
          p.trail.push({{ x: rpx, y: rpy }});
          if(p.trail.length > 7) p.trail.shift();

          return {{ p, rpx, rpy, sc, z2 }};
        }});

        // Sort by depth (back to front)
        proj.sort((a, b) => a.z2 - b.z2);

        // Draw particles
        proj.forEach(({{ p, rpx, rpy, sc }}) => {{
          const alpha = 0.14 + sc * 0.68;
          const sz    = p.size * sc * 1.3;

          // Draw trail
          if(p.trail.length > 2){{
            ctx.beginPath();
            ctx.moveTo(p.trail[0].x, p.trail[0].y);
            for(let k = 1; k < p.trail.length; k++)
              ctx.lineTo(p.trail[k].x, p.trail[k].y);
            ctx.strokeStyle = `rgba(${{p.color}},${{alpha * 0.18}})`;
            ctx.lineWidth = sz * 0.4;
            ctx.lineCap = 'round';
            ctx.stroke();
          }}

          // Draw particle glow
          const grd = ctx.createRadialGradient(rpx, rpy, 0, rpx, rpy, sz * 2.5);
          grd.addColorStop(0, `rgba(${{p.color}},${{alpha * 0.32}})`);
          grd.addColorStop(1, `rgba(${{p.color}},0)`);
          ctx.beginPath();
          ctx.arc(rpx, rpy, sz * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();

          // Draw particle core
          ctx.beginPath();
          ctx.arc(rpx, rpy, Math.max(sz * 0.5, 0.5), 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${{p.color}},${{alpha}})`;
          ctx.fill();
        }});

        requestAnimationFrame(frame);
      }}

      frame();
      window.addEventListener('resize', resize);
    }})();
    </script>
    """
