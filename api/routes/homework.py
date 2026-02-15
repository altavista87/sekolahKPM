"""Homework routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from api.schemas.homework import (
    HomeworkCreate, 
    HomeworkUpdate, 
    HomeworkResponse,
    HomeworkListResponse,
    HomeworkComplete
)
from database.models import Homework, User, Student

router = APIRouter()


@router.get("", response_model=HomeworkListResponse)
@limiter.limit("100/minute")
async def list_homework(
    request: Request,
    student_id: Optional[UUID] = Query(None, description="Filter by student ID"),
    status: Optional[str] = Query(None, pattern="^(pending|in_progress|completed|cancelled)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List homework with optional filters.
    
    Parents can only see homework for their students.
    Teachers can see all homework they created.
    """
    query = select(Homework)
    
    # Apply filters
    filters = []
    if student_id:
        filters.append(Homework.student_id == student_id)
    if status:
        filters.append(Homework.status == status)
    
    # Apply user-based filtering
    if current_user.role == "parent":
        # Parents can only see homework for their students
        student_query = select(Student.id).where(Student.parent_id == current_user.id)
        student_result = await db.execute(student_query)
        student_ids = [s[0] for s in student_result.all()]
        
        if student_id and student_id not in student_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        elif not student_id:
            filters.append(Homework.student_id.in_(student_ids))
    
    elif current_user.role == "teacher":
        # Teachers can see homework they created
        if not student_id:
            filters.append(Homework.teacher_id == current_user.id)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(select(Homework).where(and_(*filters) if filters else True).subquery())
    total_result = await db.execute(select(count_query.subquery().c.id))
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    homework_list = result.scalars().all()
    
    return HomeworkListResponse(
        homework=homework_list,
        total=total,
        page=(skip // limit) + 1,
        per_page=limit
    )


@router.post("", response_model=HomeworkResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_homework(
    request: Request,
    hw_data: HomeworkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new homework.
    
    Only teachers and admins can create homework.
    """
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create homework"
        )
    
    # Verify student exists and user has permission
    student = await db.get(Student, hw_data.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Create homework
    homework = Homework(
        student_id=hw_data.student_id,
        teacher_id=current_user.id,
        subject=hw_data.subject,
        title=hw_data.title,
        description=hw_data.description,
        due_date=hw_data.due_date,
        priority=hw_data.priority,
        raw_text=hw_data.raw_text,
        image_urls=hw_data.image_urls or [],
        file_urls=hw_data.file_urls or [],
    )
    
    db.add(homework)
    await db.commit()
    await db.refresh(homework)
    
    return homework


@router.get("/{homework_id}", response_model=HomeworkResponse)
async def get_homework(
    homework_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get homework by ID.
    """
    homework = await db.get(Homework, homework_id)
    
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found"
        )
    
    # Check permissions
    student = await db.get(Student, homework.student_id)
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    elif current_user.role == "teacher" and homework.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return homework


@router.patch("/{homework_id}", response_model=HomeworkResponse)
async def update_homework(
    homework_id: UUID,
    hw_update: HomeworkUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update homework.
    
    Only the creating teacher or admin can update homework.
    """
    homework = await db.get(Homework, homework_id)
    
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and homework.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creating teacher can update homework"
        )
    
    # Update fields
    update_data = hw_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(homework, field, value)
    
    await db.commit()
    await db.refresh(homework)
    
    return homework


@router.patch("/{homework_id}/complete", response_model=HomeworkResponse)
async def complete_homework(
    homework_id: UUID,
    complete_data: HomeworkComplete = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark homework as completed.
    
    Parents can mark homework as completed for their students.
    """
    from datetime import datetime
    
    homework = await db.get(Homework, homework_id)
    
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found"
        )
    
    # Check permissions
    student = await db.get(Student, homework.student_id)
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    homework.status = "completed"
    homework.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(homework)
    
    return homework


@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(
    homework_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete homework.
    
    Only the creating teacher or admin can delete homework.
    """
    homework = await db.get(Homework, homework_id)
    
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and homework.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creating teacher can delete homework"
        )
    
    await db.delete(homework)
    await db.commit()
    
    return None
