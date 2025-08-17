from datetime import datetime
from models.models import EmotionEvent

async def update_emotional_summary(db_conn, event: EmotionEvent):
    """
    Inserts or updates the emotional events summary for a user on a given day.
    """
    date_string = event.timestamp.split("T")[0]
    summary_date = datetime.strptime(date_string, "%Y-%m-%d").date()
    metrics = event.emotion_event.metrics
    
    query = """
    INSERT INTO emotional_events_summary (user_id, summary_date, avg_positivity_score, avg_intensity_score, avg_stress_level, event_count, updated_at)
    VALUES ($1, $2, $3, $4, $5, 1, NOW())
    ON CONFLICT (user_id, summary_date)
    DO UPDATE SET
        avg_positivity_score = (emotional_events_summary.avg_positivity_score * emotional_events_summary.event_count + EXCLUDED.avg_positivity_score) / (emotional_events_summary.event_count + 1),
        avg_intensity_score = (emotional_events_summary.avg_intensity_score * emotional_events_summary.event_count + EXCLUDED.avg_intensity_score) / (emotional_events_summary.event_count + 1),
        avg_stress_level = (emotional_events_summary.avg_stress_level * emotional_events_summary.event_count + EXCLUDED.avg_stress_level) / (emotional_events_summary.event_count + 1),
        event_count = emotional_events_summary.event_count + 1,
        updated_at = NOW();
    """
    
    await db_conn.execute(
        query, 
        event.user_id, 
        summary_date,
        metrics.positivity, 
        metrics.intensity, 
        metrics.stress_level
    )
