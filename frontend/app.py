"""MusicLore Streamlit frontend — indie music aesthetic."""

import base64
import re
import urllib.parse
from pathlib import Path

import streamlit as st
import httpx
import plotly.graph_objects as go
import pandas as pd
import streamlit.components.v1 as components

API_URL = "http://localhost:8080/chat"
BG_PATH = Path(__file__).resolve().parent / "bg.jpg"

# ── Page config ──────────────────────────────────────────────
st.set_page_config(page_title="MusicLore", page_icon="🎸", layout="wide")

# ── Background image as base64 ───────────────────────────────
bg_b64 = ""
if BG_PATH.exists():
    with open(BG_PATH, "rb") as f:
        bg_b64 = base64.b64encode(f.read()).decode()

bg_css = ""
if bg_b64:
    bg_css = f"""
    .stApp {{
        background-image: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.88)),
                          url("data:image/jpeg;base64,{bg_b64}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}
    """
else:
    bg_css = """
    .stApp {
        background-color: #0a0a0a !important;
    }
    """

# ── CSS ──────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');

/* ── Global ── */
{bg_css}
.stApp {{
    color: #e8e6e1 !important;
    font-family: 'DM Sans', sans-serif !important;
}}

/* Hide Streamlit chrome */
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}

/* ── Typography ── */
h1, h2, h3, h4 {{
    font-family: 'Space Mono', monospace !important;
    color: #e8e6e1 !important;
}}
p, li, span, div {{
    font-family: 'DM Sans', sans-serif;
}}
.stMarkdown p, .stMarkdown li {{
    color: #e8e6e1 !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
}}

/* ── Chat input ── */
[data-testid="stChatInput"] {{
    background: transparent !important;
}}
[data-testid="stChatInput"] textarea {{
    background: #141414 !important;
    border: 1px solid #2a2a2a !important;
    color: #e8e6e1 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
}}
[data-testid="stChatInput"] textarea:focus {{
    border-color: #c45d3e !important;
    box-shadow: none !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
    color: #555 !important;
}}
[data-testid="stChatInput"] button {{
    background: #c45d3e !important;
    color: #0a0a0a !important;
    border-radius: 6px !important;
}}

/* Hide default chat message containers */
[data-testid="stChatMessage"] {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}}
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessage"] .stChatMessageAvatarContainer,
[data-testid="stChatMessage"] > div:first-child {{
    display: none !important;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: #0a0a0a; }}
::-webkit-scrollbar-thumb {{ background: #2a2a2a; border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: #c45d3e; }}

/* ── Plotly ── */
.js-plotly-plot {{ border-radius: 8px; }}

/* ── Block container ── */
.block-container {{
    padding-top: 2rem !important;
    padding-bottom: 0 !important;
}}

/* ── Spinner ── */
[data-testid="stSpinner"] > div {{
    color: #555 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Layout: 3 columns, content in center ─────────────────────
_left, center, _right = st.columns([2, 5, 2])

with center:
    # ── Header ───────────────────────────────────────────────
    st.markdown("""
    <div style="padding:20px 0 16px;">
        <div style="font-family:'Space Mono',monospace; font-size:32px; color:#e8e6e1; letter-spacing:4px; font-weight:700;">
            MusicLore
        </div>
        <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:#888; font-style:italic; margin-top:2px;">
            Explore the underground
        </div>
        <div style="height:1px; background:#2a2a2a; margin-top:16px;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Render helpers ───────────────────────────────────────

    def render_user_msg(text: str):
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(f"""
        <div style="display:flex; justify-content:flex-end; margin:1rem 0;">
          <div style="background:#1a1a1a; border:1px solid #2a2a2a; border-radius:12px;
                      padding:12px 18px; max-width:70%; color:#e8e6e1; font-size:14px;
                      font-family:'DM Sans',sans-serif; line-height:1.6;">
            {safe}
          </div>
        </div>
        """, unsafe_allow_html=True)

    def render_ai_msg(text: str):
        st.markdown("""
        <div style="margin:1rem 0 0.4rem;">
          <div style="color:#c45d3e; font-size:11px; font-family:'Space Mono',monospace;
                      text-transform:uppercase; letter-spacing:2px; margin-bottom:6px;">
            musiclore
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(text, unsafe_allow_html=True)

    def render_timeline(data: dict):
        entries = data.get("entries", [])
        if not entries:
            return
        df = pd.DataFrame(entries)
        df = df.dropna(subset=["year"])
        df["year"] = df["year"].astype(int)
        df = df.sort_values("year")
        if "tier" not in df.columns:
            df["tier"] = "unknown"

        color_map = {
            "niche": "#c45d3e",
            "underground": "#7a9e7e",
            "mid": "#888888",
            "mainstream": "#444444",
            "unknown": "#333333",
        }

        fig = go.Figure()
        for tier, color in color_map.items():
            subset = df[df["tier"] == tier]
            if subset.empty:
                continue
            fig.add_trace(go.Bar(
                x=subset["year"],
                y=subset["artist"],
                orientation="h",
                name=tier,
                marker_color=color,
                hovertemplate="%{y}<br>%{x}<extra></extra>",
            ))

        genre = data.get("genre", "")
        fig.update_layout(
            title=dict(
                text=f"{genre} Timeline",
                font=dict(family="Space Mono", size=14, color="#c45d3e"),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color="#e8e6e1", size=12),
            xaxis=dict(gridcolor="#1a1a1a", title="", zeroline=False),
            yaxis=dict(gridcolor="#1a1a1a", title="", autorange="reversed"),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="#888", size=11, family="Space Mono"),
            ),
            height=max(400, len(df) * 26),
            margin=dict(l=0, r=0, t=40, b=20),
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    def render_recommendations(data: dict):
        seed = data.get("seed_artist", "")
        if seed:
            st.markdown(f"""
            <div style="font-family:'Space Mono',monospace; font-size:12px; color:#888;
                        text-transform:uppercase; letter-spacing:2px; margin:20px 0 12px;">
                Recommendations based on {seed}
            </div>
            """, unsafe_allow_html=True)

        for card in data.get("cards", []):
            artist = card.get("artist", "Unknown")
            reason = card.get("reason", "")
            path = card.get("path", [])
            listeners = card.get("listeners")
            embed_url = card.get("embed_url", "")

            listeners_html = ""
            if listeners is not None:
                try:
                    listeners_html = (
                        f'<span style="background:#1a2e1a; color:#7a9e7e; font-size:11px;'
                        f' padding:3px 10px; border-radius:20px; margin-left:10px;'
                        f' font-family:\'Space Mono\',monospace;">'
                        f'{int(listeners):,} listeners</span>'
                    )
                except (ValueError, TypeError):
                    pass

            reason_html = ""
            if reason:
                safe_reason = str(reason).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                reason_html = (
                    f'<p style="color:#888; font-size:13px; margin-top:10px; line-height:1.6;'
                    f' font-family:\'DM Sans\',sans-serif;">{safe_reason}</p>'
                )

            path_html = ""
            if path:
                path_str = " &rarr; ".join(str(p) for p in path)
                path_html = (
                    f'<div style="margin-top:10px;">'
                    f'<span style="font-size:11px; font-family:\'Space Mono\',monospace;'
                    f' color:#c45d3e;">influence path: </span>'
                    f'<span style="font-size:12px; color:#888;'
                    f' font-family:\'DM Sans\',sans-serif;">{path_str}</span>'
                    f'</div>'
                )

            st.markdown(
                f'<div style="background:#141414; border:1px solid #2a2a2a; border-radius:12px;'
                f' padding:20px; margin:12px 0;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center;'
                f' flex-wrap:wrap;">'
                f'<div>'
                f'<span style="font-family:\'Space Mono\',monospace; font-size:18px;'
                f' color:#e8e6e1;">{artist}</span>'
                f'{listeners_html}'
                f'</div></div>'
                f'{reason_html}'
                f'{path_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            if embed_url and "youtube.com/embed/" in embed_url:
                components.iframe(embed_url, height=80)
            else:
                yt_query = urllib.parse.quote(f"{artist} full album")
                st.markdown(
                    f'<div style="margin:-4px 0 8px 0;">'
                    f'<a href="https://www.youtube.com/results?search_query={yt_query}"'
                    f' target="_blank"'
                    f' style="font-size:11px; color:#555; text-decoration:none;'
                    f' font-family:\'Space Mono\',monospace;">'
                    f'&#9655; Search on YouTube</a></div>',
                    unsafe_allow_html=True,
                )

    def render_microcourse(data: dict):
        topic = data.get("topic", "")
        if topic:
            st.markdown(
                f'<div style="font-family:\'Space Mono\',monospace; font-size:12px; color:#c45d3e;'
                f' text-transform:uppercase; letter-spacing:2px; margin:20px 0 16px;">'
                f'{topic}</div>',
                unsafe_allow_html=True,
            )

        for section in data.get("sections", []):
            title = section.get("title", "")
            content = section.get("content", "")
            sources = section.get("sources", [])

            source_html = ""
            if sources:
                links = " ".join(
                    f'<a href="{s}" target="_blank" style="font-size:11px; color:#555;'
                    f' text-decoration:none; font-family:\'Space Mono\',monospace;">[source]</a>'
                    for s in sources if s
                )
                source_html = f'<div style="margin-top:6px;">{links}</div>'

            # Escape content for safety but allow newlines
            safe_content = str(content).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_content = safe_content.replace("\n", "<br>")

            st.markdown(
                f'<div style="margin:24px 0;">'
                f'<div style="font-family:\'Space Mono\',monospace; font-size:13px; color:#c45d3e;'
                f' text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">{title}</div>'
                f'<div style="color:#e8e6e1; font-size:14px; line-height:1.8;'
                f' font-family:\'DM Sans\',sans-serif;">{safe_content}</div>'
                f'{source_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

        embed_url = data.get("embed_url", "")
        if embed_url and "youtube.com/embed/" in embed_url:
            components.iframe(embed_url, height=80)

    def render_structured(data: dict):
        if not data or not isinstance(data, dict):
            return
        try:
            t = data.get("type")
            if t == "timeline":
                render_timeline(data)
            elif t == "recommendations":
                render_recommendations(data)
            elif t == "microcourse":
                render_microcourse(data)
        except Exception:
            pass

    # ── Display chat history ─────────────────────────────────
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            render_user_msg(msg["content"])
        else:
            render_ai_msg(msg["content"])
            if msg.get("structured_data"):
                render_structured(msg["structured_data"])

    # ── Chat input ───────────────────────────────────────────
    if prompt := st.chat_input("输入你想探索的音乐..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_user_msg(prompt)

        loading = st.empty()
        loading.markdown(
            '<div style="color:#555; font-size:12px; font-family:\'Space Mono\',monospace;'
            ' letter-spacing:1px; margin:1rem 0;">'
            '&#x27F3; searching the graph...</div>',
            unsafe_allow_html=True,
        )

        try:
            resp = httpx.post(API_URL, json={"message": prompt}, timeout=180)
            resp.raise_for_status()
            result = resp.json()

            text = result.get("text", "")
            structured = result.get("structured_data")

            display_text = re.sub(r'```json\s*\n?.*?\n?\s*```', '', text, flags=re.DOTALL).strip()

            loading.empty()

            if display_text:
                render_ai_msg(display_text)
            if structured:
                render_structured(structured)

            st.session_state.messages.append({
                "role": "assistant",
                "content": display_text,
                "structured_data": structured,
            })

        except httpx.TimeoutException:
            loading.empty()
            st.markdown(
                '<div style="color:#c45d3e; font-size:13px; font-family:\'Space Mono\',monospace;'
                ' margin:1rem 0;">timeout — try again</div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            loading.empty()
            st.markdown(
                f'<div style="color:#c45d3e; font-size:13px; font-family:\'Space Mono\',monospace;'
                f' margin:1rem 0;">error — {str(e)[:100]}</div>',
                unsafe_allow_html=True,
            )

    # ── Footer ───────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center; padding:40px 0 20px; border-top:1px solid #1a1a1a;'
        ' margin-top:40px;">'
        '<p style="font-size:11px; color:#444; font-family:\'Space Mono\',monospace;'
        ' letter-spacing:1px;">'
        'DATA &middot; MUSICBRAINZ (CC0) &middot; WIKIDATA (CC0) &middot;'
        ' WIKIPEDIA (CC BY-SA) &middot; LAST.FM'
        '</p></div>',
        unsafe_allow_html=True,
    )
