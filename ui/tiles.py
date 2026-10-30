
"""ui/tiles.py — Factory floor and inventory tiles."""

from __future__ import annotations

import html
import streamlit as st


# ============================================================
# CSS
# ============================================================

_CSS = """
<style>

.tx-tile {
    position: relative;
    box-sizing: border-box;
    height: 240px;
    width: 100%;
    overflow: hidden;
    padding: 18px;
    border-radius: 15px;
    border: 1px solid rgba(255,255,255,.18);

    background:
        linear-gradient(135deg, rgba(255,255,255,.09), transparent 48%),
        repeating-linear-gradient(
            0deg,
            rgba(255,255,255,.025) 0 1px,
            transparent 1px 4px
        ),
        repeating-linear-gradient(
            90deg,
            rgba(0,0,0,.035) 0 1px,
            transparent 1px 4px
        ),
        var(--tile-color, #263746);

    box-shadow: 0 8px 22px rgba(0,0,0,.18);
    transition: transform .18s ease, box-shadow .18s ease;
    color: white;
}

.tx-tile:hover {
    transform: translateY(-3px);
    box-shadow: 0 13px 28px rgba(0,0,0,.27);
}

/* Decorative inner border */

.tx-tile::before {
    content: "";
    position: absolute;
    inset: 9px;
    border: 1px dashed rgba(255,255,255,.28);
    border-radius: 10px;
    pointer-events: none;
}

/* Decorative circular pattern */

.tx-tile::after {
    content: "";
    position: absolute;
    width: 120px;
    height: 120px;
    right: -34px;
    bottom: -42px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,.18);
    box-shadow:
        0 0 0 12px rgba(255,255,255,.035),
        0 0 0 25px rgba(255,255,255,.025);
    pointer-events: none;
}

/* Top section */

.tx-tile-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    position: relative;
    z-index: 1;
}

.tx-id {
    font-size: 11px;
    letter-spacing: 2px;
    font-weight: 800;
    opacity: .82;
}

.tx-status {
    border: 1px solid rgba(255,255,255,.42);
    border-radius: 99px;
    padding: 5px 9px;
    font-size: 10px;
    letter-spacing: 1px;
    font-weight: 800;
    background: rgba(0,0,0,.16);
}

/* Icon */

.tx-icon {
    position: relative;
    z-index: 1;
    font-size: 48px;
    line-height: 1;
    margin-top: 28px;
    filter: drop-shadow(0 4px 5px rgba(0,0,0,.18));
}

/* Machine name */

.tx-name {
    position: relative;
    z-index: 1;
    font-size: 20px;
    line-height: 1.15;
    font-weight: 850;
    margin-top: 13px;
    max-width: 88%;
    overflow-wrap: anywhere;
}

/* Machine information */

.tx-meta {
    position: relative;
    z-index: 1;
    font-size: 12px;
    opacity: .82;
    margin-top: 8px;
}

/* Inventory gauge */

.tx-gauge {
    position: relative;
    z-index: 1;
    height: 5px;
    max-width: 55%;
    margin-top: 12px;
    border-radius: 3px;
    background: rgba(255,255,255,.2);
    overflow: hidden;
}

.tx-gauge i {
    display: block;
    height: 100%;
    background: rgba(255,255,255,.9);
}

/* Bottom tag */

.tx-tag {
    position: absolute;
    right: 16px;
    bottom: 14px;
    z-index: 2;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1.6px;
    padding: 7px 9px;
    border-radius: 4px;
    background: rgba(0,0,0,.2);
    border: 1px solid rgba(255,255,255,.24);
}

/* Hover information panel */

/* Hover information panel */

.tx-tile {
    isolation: isolate;
}

.tx-peek {
    position: absolute;
    inset: 0;
    z-index: 20;
    padding: 20px;
    box-sizing: border-box;
    background: rgba(9, 15, 24, .97);

    opacity: 0;
    visibility: hidden;
    transform: translateY(10px);

    transition:
        opacity .2s ease,
        transform .2s ease,
        visibility .2s ease;

    pointer-events: none;
}

/* Hover works independently for every tile */

.tx-tile:hover .tx-peek {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}
.tx-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-size: 12.5px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,.12);
}

.tx-row span {
    opacity: .65;
}

.tx-row b {
    font-weight: 700;
    text-align: right;
    overflow-wrap: anywhere;
}

.tx-hint {
    margin-top: 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.4px;
    opacity: .8;
}

/* Failed machine animation */

.tx-failed {
    animation: tx-pulse 1.8s infinite;
}

@keyframes tx-pulse {
    0%, 100% {
        box-shadow: 0 8px 22px rgba(0,0,0,.18);
    }

    50% {
        box-shadow: 0 8px 26px rgba(239,68,68,.38);
    }
}

/* Dialog styling */

.dlg-head {
    display: flex;
    gap: 16px;
    align-items: center;
    margin-bottom: 6px;
}

.dlg-icon {
    font-size: 52px;
    line-height: 1;
}

.dlg-id {
    opacity: .6;
    font-size: 13px;
}

.dlg-name {
    font-size: 26px;
    font-weight: 700;
    line-height: 1.1;
}

/* Reduced motion */

@media (prefers-reduced-motion: reduce) {
    .tx-tile,
    .tx-peek {
        transition: none;
    }

    .tx-failed {
        animation: none;
    }
}

</style>
"""


def inject_tile_css() -> None:
    """Inject tile styling once per Streamlit render."""
    st.html(_CSS)


# ============================================================
# ICON HELPERS
# ============================================================

_MACHINE_ICONS = [
    (("loom", "weav"), "🧵"),
    (("dye", "bleach", "wash"), "🎨"),
    (("spin", "twist", "wind", "yarn", "knit"), "🧶"),
    (("cut", "stitch", "sew", "garment"), "✂️"),
    (("print", "finish", "calender", "stenter", "press", "coat"), "🖨️"),
]

_MATERIAL_ICONS = [
    (("cotton", "linen", "jute", "hemp", "fibre", "fiber"), "☁️"),
    (("polyester", "nylon", "synthetic", "acrylic"), "🧪"),
    (("viscose", "rayon", "modal", "lyocell"), "🧵"),
    (("silk", "wool", "cashmere"), "🧶"),
    (("yarn", "thread", "spandex", "elastic"), "🧶"),
    (("dye", "pigment", "colour", "color", "ink"), "🎨"),
    (("chemical", "bleach", "solvent"), "⚗️"),
    (("water",), "💧"),
    (("fabric", "textile", "cloth"), "🪡"),
    (("button", "zipper", "accessory"), "🔘"),
    (("packaging", "carton", "box"), "📦"),
]


def _pick(text, table, default):
    text = str(text).lower()

    for words, icon in table:
        if any(word in text for word in words):
            return icon

    return default


def machine_icon(machine_id, machine):
    return _pick(
        f"{machine.get('name', '')} {machine_id}",
        _MACHINE_ICONS,
        "⚙️",
    )


def material_icon(material_id, material):
    return _pick(
        f"{material.get('name', '')} {material_id}",
        _MATERIAL_ICONS,
        "📦",
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _esc(value):
    """Escape dynamic text before inserting it into HTML."""
    return html.escape(str(value))


# ============================================================
# TILE HTML GENERATOR
# ============================================================

def _tile_markup(
    *,
    color,
    failed,
    tile_id,
    badge,
    icon,
    name,
    meta,
    peek_rows,
    hint,
    gauge=None,
):
    """Generate HTML for a single factory or inventory tile."""

    rows = "".join(
        f'<div class="tx-row">'
        f'<span>{_esc(key)}</span>'
        f'<b>{_esc(value)}</b>'
        f'</div>'
        for key, value in peek_rows
    )

    gauge_html = ""

    if gauge is not None:
        gauge = max(0.0, min(float(gauge), 1.0))

        gauge_html = (
            f'<div class="tx-gauge">'
            f'<i style="width:{gauge * 100:.0f}%"></i>'
            f'</div>'
        )

    failed_class = " tx-failed" if failed else ""

    markup = f"""
    <div class="tx-tile{failed_class}"
         style="--tile-color:{color}">

        <div class="tx-tile-top">
            <span class="tx-id">{_esc(tile_id)}</span>
            <span class="tx-status">{_esc(badge)}</span>
        </div>

        <div class="tx-icon">{icon}</div>

        <div class="tx-name">{_esc(name)}</div>

        <div class="tx-meta">{_esc(meta)}</div>

        {gauge_html}

        <div class="tx-tag">
            OPEN ↗
        </div>

        <div class="tx-peek">

            <div class="tx-peek-title">
                {_esc(name)}
            </div>

            {rows}

            <div class="tx-hint">
                {_esc(hint)}
            </div>

        </div>

    </div>
    """

    return markup


# ============================================================
# MACHINE TILES
# ============================================================

_STATUS_COLORS = {
    "RUNNING": "#17634f",
    "IDLE": "#805d20",
    "FAILED": "#7d292d",
    "MAINTENANCE": "#66508a",
}


def machine_tile(machine_id, machine):
    """
    Render a machine tile.

    Returns:
        True if the control panel button is clicked.
        False otherwise.
    """

    status = str(
        machine.get("status", "UNKNOWN")
    ).upper()

    name = machine.get("name", machine_id)

    capacity = machine.get(
        "capacity_m_per_hr",
        "N/A",
    )

    order = machine.get(
        "assigned_order_id"
    ) or "No order"

    compatible = machine.get(
        "compatible_materials"
    ) or []

    markup = _tile_markup(
        color=_STATUS_COLORS.get(
            status,
            "#344454",
        ),

        failed=status == "FAILED",

        tile_id=machine_id,

        badge=status,

        icon=machine_icon(
            machine_id,
            machine,
        ),

        name=name,

        meta=f"{capacity} m/hr · {order}",

        peek_rows=[
            ("Capacity", f"{capacity} m/hr"),
            ("Order", order),

            (
                "Repair time",
                f"{machine.get('maintenance_duration_hrs', 'N/A')} hrs",
            ),

            (
                "Spare part",
                machine.get(
                    "required_spare_part",
                    "Not specified",
                ),
            ),

            (
                "Materials",
                f"{len(compatible)} compatible",
            ),
        ],

        hint="CLICK TO OPEN CONTROL PANEL",
    )

    with st.container(key=f"tile_machine_{machine_id}"):

        # Direct HTML rendering
        st.html(markup)

        clicked = st.button(
            "⚙️ Open Control Panel",
            key=f"select_{machine_id}",
            use_container_width=True,
        )

        return clicked


# ============================================================
# MACHINE GRID
# ============================================================

def render_machine_grid(machines, columns=3):
    """
    Render all machine tiles.

    Returns:
        machine_id if clicked.
        None otherwise.
    """

    items = list(machines.items())

    if not items:
        st.info("No machines configured.")
        return None

    columns = max(1, int(columns))

    for start in range(0, len(items), columns):

        row_items = items[start:start + columns]

        cols = st.columns(columns, gap="medium")

        for col, (machine_id, machine) in zip(
            cols,
            row_items,
        ):

            with col:

                if machine_tile(machine_id, machine):
                    return machine_id

    return None


def inventory_tile(material_id, material):

    stock = _num(material.get("stock_kg", 0))
    reserved = _num(material.get("reserved_kg", 0))

    available = max(0.0, stock - reserved)
    ratio = min(available / stock, 1.0) if stock > 0 else 0.0

    if available <= 0:
        color = "#7d292d"
        badge = "OUT OF STOCK"
    elif ratio < 0.25:
        color = "#805d20"
        badge = "LOW STOCK"
    else:
        color = "#17634f"
        badge = "IN STOCK"

    name = material.get("name", material_id)

    markup = _tile_markup(
        color=color,
        failed=available <= 0,
        tile_id=material_id,
        badge=badge,
        icon=material_icon(material_id, material),
        name=name,
        meta=f"{available:,.1f} kg available",
        gauge=ratio,

        peek_rows=[
            ("Total stock", f"{stock:,.1f} kg"),
            ("Reserved stock", f"{reserved:,.1f} kg"),
            ("Available stock", f"{available:,.1f} kg"),
            ("Free stock", f"{ratio * 100:.1f}%"),
        ],

        hint="INVENTORY DETAILS ↗",
    )

    with st.container():

        st.html(markup)

        return st.button(
            "📦 View Inventory",
            key=f"open_material_{material_id}",
            use_container_width=True,
        )
# ============================================================
# INVENTORY GRID
# ============================================================

def render_inventory_grid(materials, columns=3):
    """
    Render all inventory tiles.

    Returns:
        material_id if clicked.
        None otherwise.
    """

    items = list(materials.items())

    if not items:
        st.info("No inventory configured.")
        return None

    columns = max(1, int(columns))

    for start in range(0, len(items), columns):

        row_items = items[start:start + columns]

        cols = st.columns(columns, gap="medium")

        for col, (material_id, material) in zip(
            cols,
            row_items,
        ):

            with col:

                if inventory_tile(material_id, material):
                    return material_id

    return None
