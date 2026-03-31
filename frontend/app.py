"""MusicLore Streamlit frontend — My Bloody Valentine–inspired aesthetic."""

import streamlit as st
import httpx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit.components.v1 as components

API_URL = "http://localhost:8080/chat"

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="MusicLore",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── MBV-inspired palette ────────────────────────────────────
# Hazy pinks, magentas, deep purples, washed-out whites
MBV_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@400;500;700&display=swap');

:root {
    --bg-deep: #0d0a12;
    --bg-card: #1a1225;
    --bg-card-hover: #231a30;
    --pink-hot: #e84393;
    --pink-soft: #fd79a8;
    --magenta: #d63384;
    --purple-wash: #6c5ce7;
    --lavender: #a29bfe;
    --text-primary: #f0e6f6;
    --text-muted: #b8a9c9;
    --white-haze: rgba(255,255,255,0.07);
}

/* Global */
.stApp {
    background: linear-gradient(170deg, #0d0a12 0%, #1a0a20 40%, #12081a 100%);
    color: var(--text-primary);
}
.stApp > header { background: transparent !important; }

/* Typography */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Space Mono', monospace !important;
    color: var(--pink-soft) !important;
    text-shadow: 0 0 30px rgba(232,67,147,0.3);
}
p, li, span, .stMarkdown p, .stMarkdown li {
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text-primary) !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid rgba(108,92,231,0.2) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(10px);
    margin-bottom: 1rem;
}
[data-testid="stChatMessage"]:hover {
    border-color: var(--pink-hot) !important;
    box-shadow: 0 0 20px rgba(232,67,147,0.15);
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    background: var(--bg-card) !important;
    border: 1px solid rgba(162,155,254,0.3) !important;
    color: var(--text-primary) !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--pink-hot) !important;
    box-shadow: 0 0 15px rgba(232,67,147,0.25) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid rgba(162,155,254,0.2) !important;
    border-radius: 8px !important;
    color: var(--lavender) !important;
    font-family: 'Space Mono', monospace !important;
}
.streamlit-expanderContent {
    background: var(--bg-card) !important;
    border: 1px solid rgba(108,92,231,0.15) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--magenta); border-radius: 3px; }

/* Divider */
hr { border-color: rgba(162,155,254,0.15) !important; }

/* Captions */
.stCaption, [data-testid="stCaption"] {
    color: var(--text-muted) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* Title glow animation */
@keyframes haze-pulse {
    0%, 100% { text-shadow: 0 0 30px rgba(232,67,147,0.3), 0 0 60px rgba(108,92,231,0.15); }
    50% { text-shadow: 0 0 40px rgba(232,67,147,0.5), 0 0 80px rgba(108,92,231,0.25); }
}
.title-glow {
    animation: haze-pulse 4s ease-in-out infinite;
    font-family: 'Space Mono', monospace !important;
    color: #fd79a8 !important;
    text-align: center;
    font-size: 2.2rem !important;
    letter-spacing: 0.15em;
    margin-bottom: 0 !important;
}
.subtitle-haze {
    text-align: center;
    color: #b8a9c9 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem;
    margin-top: 0.2rem;
    letter-spacing: 0.08em;
}

/* Noise overlay for MBV feel */
.noise-overlay {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none;
    z-index: 0;
    opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
</style>
<div class="noise-overlay"></div>
"""
st.markdown(MBV_CSS, unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown('<p class="title-glow">🎸 MusicLore</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-haze">小众音乐发掘 Agent · Post-Punk · Shoegaze · Krautrock</p>', unsafe_allow_html=True)
st.markdown("---")

# ── Session state ────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Renderers ────────────────────────────────────────────────
TIER_COLORS = {
    "mainstream": "#e84393",
    "mid": "#fd79a8",
    "underground": "#6c5ce7",
    "niche": "#a29bfe",
    "unknown": "#636e72",
}


def render_timeline(data: dict):
    entries = data.get("entries", [])
    if not entries:
        return
    df = pd.DataFrame(entries)
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df = df.sort_values("year")
    df["tier"] = df.get("tier", pd.Series(["unknown"] * len(df)))

    fig = px.bar(
        df, x="year", y="artist", color="tier",
        orientation="h",
        color_discrete_map=TIER_COLORS,
        hover_data=["country", "listeners"],
        title=f"⏳ {data.get('genre', '')} Timeline",
    )
    fig.update_layout(
        plot_bgcolor="rgba(13,10,18,0.8)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Mono", color="#f0e6f6"),
        title_font=dict(color="#fd79a8", size=18),
        xaxis=dict(gridcolor="rgba(162,155,254,0.1)", title="Year"),
        yaxis=dict(gridcolor="rgba(162,155,254,0.1)", title="", autorange="reversed"),
        legend=dict(bgcolor="rgba(26,18,37,0.8)", font=dict(color="#b8a9c9")),
        height=max(400, len(df) * 28),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_recommendations(data: dict):
    seed = data.get("seed_artist", "")
    st.markdown(f"#### 🔮 基于 **{seed}** 的推荐")
    cards = data.get("cards", [])
    for card in cards:
        artist = card.get("artist", "Unknown")
        reason = card.get("reason", "")
        path = card.get("path", [])
        listeners = card.get("listeners", "N/A")
        embed_url = card.get("embed_url", "")

        with st.expander(f"🎵 {artist} — {listeners:,} listeners" if isinstance(listeners, int) else f"🎵 {artist}"):
            if reason:
                st.markdown(f"**推荐理由：** {reason}")
            if path:
                path_str = " → ".join(path)
                st.markdown(f"**影响路径：** `{path_str}`")
            if listeners and isinstance(listeners, int):
                st.caption(f"Last.fm listeners: {listeners:,}")
            if embed_url:
                components.iframe(embed_url, height=200)


def render_microcourse(data: dict):
    topic = data.get("topic", "")
    st.markdown(f"#### 📖 {topic}")
    for section in data.get("sections", []):
        st.markdown(f"**{section.get('title', '')}**")
        st.markdown(section.get("content", ""))
        sources = section.get("sources", [])
        if sources:
            for src in sources:
                st.caption(f"📎 {src}")
    embed_url = data.get("embed_url", "")
    if embed_url:
        st.markdown("**🎧 Listen**")
        components.iframe(embed_url, height=200)


def render_structured(data: dict):
    t = data.get("type")
    if t == "timeline":
        render_timeline(data)
    elif t == "recommendations":
        render_recommendations(data)
    elif t == "microcourse":
        render_microcourse(data)


# ── Chat history display ────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("structured_data"):
            render_structured(msg["structured_data"])

# ── Chat input ───────────────────────────────────────────────
if prompt := st.chat_input("问我关于 Post-Punk、Shoegaze、Krautrock 的任何问题..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("🌀 正在探索音乐知识图谱..."):
            try:
                resp = httpx.post(API_URL, json={"message": prompt}, timeout=180)
                resp.raise_for_status()
                result = resp.json()

                text = result.get("text", "")
                structured = result.get("structured_data")

                # Clean out raw JSON blocks from display text
                import re
                display_text = re.sub(r'```json\s*\n?.*?\n?\s*```', '', text, flags=re.DOTALL).strip()
                if display_text:
                    st.markdown(display_text)

                if structured:
                    render_structured(structured)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": display_text,
                    "structured_data": structured,
                })

            except httpx.TimeoutException:
                st.error("⏰ 请求超时，请稍后重试")
            except Exception as e:
                st.error(f"❌ 请求失败: {e}")

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption("Data: MusicBrainz (CC0) · Wikidata (CC0) · Wikipedia (CC BY-SA) · Powered by Last.fm")
