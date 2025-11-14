"""
Metrics Router - API endpoints for Lean Kanban metrics and analytics

This module provides endpoints for key flow metrics:
- Throughput
- Cycle Time
- Lead Time
- Work In Progress (WIP)
- Cumulative Flow Diagram (CFD)
- Blocked Stories tracking
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.metrics_service import MetricsService


router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/throughput",
    summary="Get throughput metrics"
)
async def get_throughput(
    project_id: int = Query(..., description="Project ID"),
    start_date: datetime = Query(..., description="Period start date (ISO format)"),
    end_date: datetime = Query(..., description="Period end date (ISO format)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate throughput (stories completed per period)

    **Throughput** measures delivery rate - a key Lean Kanban flow metric.

    Returns:
    - Period information (start, end, days)
    - Number of stories completed
    - Throughput per day

    **Example query:**
    ```
    GET /metrics/throughput?project_id=1&start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59
    ```

    **Use case:** Track delivery velocity over sprints or weeks
    """
    result = await MetricsService.get_throughput(project_id, start_date, end_date, db)
    return result


@router.get(
    "/cycle-time",
    summary="Get average cycle time"
)
async def get_average_cycle_time(
    project_id: int = Query(..., description="Project ID"),
    start_date: Optional[datetime] = Query(None, description="Filter: completed after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter: completed before this date"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate average cycle time (IN_PROGRESS to DONE)

    **Cycle time** measures how long work takes once started.
    This is a critical efficiency metric in Lean Kanban.

    Returns:
    - Number of stories analyzed
    - Average cycle time in hours
    - Min and max cycle times

    **Lower cycle time = faster delivery**

    **Example query:**
    ```
    GET /metrics/cycle-time?project_id=1&start_date=2024-01-01T00:00:00
    ```

    **Use case:** Identify process inefficiencies, set service level expectations
    """
    result = await MetricsService.get_average_cycle_time(
        project_id, start_date, end_date, db
    )
    return result


@router.get(
    "/lead-time",
    summary="Get average lead time"
)
async def get_average_lead_time(
    project_id: int = Query(..., description="Project ID"),
    start_date: Optional[datetime] = Query(None, description="Filter: completed after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter: completed before this date"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate average lead time (TODO to DONE)

    **Lead time** measures total time from request to delivery.
    It includes waiting time before work starts.

    Returns:
    - Number of stories analyzed
    - Average lead time in hours
    - Min and max lead times

    **Lead time = Wait time + Cycle time**

    **Example query:**
    ```
    GET /metrics/lead-time?project_id=1
    ```

    **Use case:** Set customer expectations, measure end-to-end efficiency
    """
    result = await MetricsService.get_average_lead_time(
        project_id, start_date, end_date, db
    )
    return result


@router.get(
    "/wip",
    summary="Get current Work In Progress"
)
async def get_current_wip(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current Work In Progress by status

    **WIP** is a fundamental Kanban metric showing current load.
    Monitoring WIP helps identify bottlenecks.

    Returns:
    - Total active WIP (excluding DONE and ARCHIVED)
    - WIP count by status

    **Lower WIP = faster flow (per Little's Law)**

    **Example query:**
    ```
    GET /metrics/wip?project_id=1
    ```

    **Use case:** Monitor system load, enforce WIP limits, identify bottlenecks
    """
    result = await MetricsService.get_current_wip(project_id, db)
    return result


@router.get(
    "/cumulative-flow",
    summary="Get Cumulative Flow Diagram data"
)
async def get_cumulative_flow(
    project_id: int = Query(..., description="Project ID"),
    start_date: datetime = Query(..., description="Period start date (ISO format)"),
    end_date: datetime = Query(..., description="Period end date (ISO format)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate Cumulative Flow Diagram (CFD) data

    **CFD** shows how work accumulates over time in each status.
    It's one of the most powerful Kanban visualizations.

    Returns:
    - Daily data points with story counts by status
    - Date range information

    **CFD helps you:**
    - Identify bottlenecks (widening bands)
    - Predict delivery dates
    - Monitor flow health
    - Spot process instability

    **How to read CFD:**
    - Vertical distance = WIP
    - Horizontal distance = Cycle time
    - Slope = Throughput

    **Example query:**
    ```
    GET /metrics/cumulative-flow?project_id=1&start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59
    ```

    **Use case:** Visualize flow over time, forecast completion dates
    """
    result = await MetricsService.get_cumulative_flow(
        project_id, start_date, end_date, db
    )
    return result


@router.get(
    "/blocked",
    summary="Get blocked stories"
)
async def get_blocked_stories(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all currently blocked stories with blocking duration

    **Blocked stories** represent impediments that need attention.
    This metric helps with impediment management.

    Returns:
    - Count of blocked stories
    - Details of each blocked story:
      - Story ID and title
      - Epic ID
      - When it was blocked
      - How long it's been blocked (hours)

    **Blocked work reduces flow efficiency**

    **Example query:**
    ```
    GET /metrics/blocked?project_id=1
    ```

    **Use case:** Daily standups, impediment management, flow optimization
    """
    result = await MetricsService.get_blocked_stories(project_id, db)
    return result
