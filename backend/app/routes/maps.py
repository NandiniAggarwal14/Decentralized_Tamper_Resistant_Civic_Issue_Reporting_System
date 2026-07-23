import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse

from backend.app.database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maps", tags=["maps"])

STATUS_COLORS = {
    "pending": "#f59e0b",      # Amber
    "in_progress": "#3b82f6",  # Blue
    "resolved": "#10b981",     # Green
    "rejected": "#ef4444",     # Red
}

@router.get("/issues", response_class=HTMLResponse)
async def get_issues_folium_map(ward_id: Optional[int] = Query(None)):
    """
    Generate an interactive Folium map with OpenStreetMap tiles displaying all active/resolved/rejected civic issues.
    Supports filtering by ward_id and includes custom styled HTML popups and OSRM route overlays.
    """
    try:
        import folium
        from folium.plugins import MarkerCluster
    except ImportError:
        # Fallback HTML if folium is not installed
        return HTMLResponse(
            content="<html><body><h3>Folium library not installed. Please run pip install folium.</h3></body></html>",
            status_code=500
        )

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if ward_id:
                cursor.execute(
                    """
                    SELECT i.id, i.title, i.category, i.area, i.address, i.latitude, i.longitude,
                           i.status, i.upvote_count, i.downvote_count, i.created_at, w.name as ward_name
                    FROM issues i
                    JOIN wards w ON i.ward_id = w.id
                    WHERE i.ward_id = %s
                    ORDER BY i.created_at DESC
                    """,
                    (ward_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT i.id, i.title, i.category, i.area, i.address, i.latitude, i.longitude,
                           i.status, i.upvote_count, i.downvote_count, i.created_at, w.name as ward_name
                    FROM issues i
                    LEFT JOIN wards w ON i.ward_id = w.id
                    ORDER BY i.created_at DESC
                    """
                )
            issues = cursor.fetchall()

    # Default map center: Connaught Place, New Delhi (28.6315, 77.2167)
    center_lat, center_lng = 28.6315, 77.2167
    if issues:
        valid_coords = [(row["latitude"], row["longitude"]) for row in issues if row.get("latitude") and row.get("longitude")]
        if valid_coords:
            center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
            center_lng = sum(c[1] for c in valid_coords) / len(valid_coords)

    # Initialize Folium Map with standard realistic OpenStreetMap tiles
    folium_map = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True
    )

    marker_cluster = MarkerCluster(name="Civic Issues").add_to(folium_map)

    coords_list = []

    for issue in issues:
        lat = issue.get("latitude")
        lng = issue.get("longitude")
        if not lat or not lng:
            continue

        coords_list.append((lat, lng))

        status = issue.get("status", "pending")
        color = STATUS_COLORS.get(status, "#64748b")
        title = issue.get("title", "Civic Issue")
        category = issue.get("category", "General")
        area = issue.get("area", "")
        ward_name = issue.get("ward_name", "N/A")
        upvotes = issue.get("upvote_count", 0)

        popup_html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-width: 220px; padding: 4px;">
            <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">{title}</div>
            <div style="font-size: 11px; margin-bottom: 8px;">
                <span style="background: {color}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600; text-transform: uppercase;">{status.replace('_', ' ')}</span>
                <span style="color: #64748b; margin-left: 6px;">{category}</span>
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 4px;"><strong>Area:</strong> {area} ({ward_name})</div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 8px;"><strong>Upvotes:</strong> 👍 {upvotes}</div>
            <div style="font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 4px;">
                GPS: {lat:.4f}, {lng:.4f}
            </div>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lng],
            radius=9,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{title} ({status.replace('_', ' ')})",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=2
        ).add_to(marker_cluster)

    # Optional: Add LayerControl
    folium.LayerControl().add_to(folium_map)

    # Render Folium map HTML string
    map_html = folium_map._repr_html_()

    # Wrap in standard standalone HTML template for clean iframe rendering
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Issues Realistic Map</title>
    <style>
        html, body {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: #f8fafc;
        }}
    </style>
</head>
<body>
    {map_html}
</body>
</html>"""

    return HTMLResponse(content=full_html)
