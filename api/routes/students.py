"""Student routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_current_parent, get_db
from api.schemas.student import StudentCreate, StudentResponse, StudentWithHomework, StudentStats
from api.schemas.homework import HomeworkResponse
from database.models import Student, Homework, User

router = APIRouter()


@router.get("/{student_id}", response_model=StudentResponse)
@limiter.limit("100/minute")
async def get_student(
    request: Request,
    student_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get student by ID.
    """
    student = await db.get(Student, student_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check permissions
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return student


@router.get("/{student_id}/homework", response_model=StudentWithHomework)
async def get_student_homework(
    student_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all homework for a student.
    """
    student = await db.get(Student, student_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check permissions
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    elif current_user.role == "teacher":
        # Teachers can only see homework they assigned
        query = select(Homework).where(
            and_(
                Homework.student_id == student_id,
                Homework.teacher_id == current_user.id
            )
        )
        result = await db.execute(query)
        homework_list = result.scalars().all()
        student.homework = homework_list
    else:
        # Load homework for parent/admin
        query = select(Homework).where(Homework.student_id == student_id)
        result = await db.execute(query)
        homework_list = result.scalars().all()
        student.homework = homework_list
    
    return student


@router.get("/{student_id}/stats", response_model=StudentStats)
async def get_student_stats(
    student_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get homework statistics for a student.
    """
    from datetime import datetime
    
    student = await db.get(Student, student_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check permissions
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get homework stats
    query = select(Homework).where(Homework.student_id == student_id)
    
    if current_user.role == "teacher":
        query = query.where(Homework.teacher_id == current_user.id)
    
    result = await db.execute(query)
    homework_list = result.scalars().all()
    
    total = len(homework_list)
    completed = sum(1 for hw in homework_list if hw.status == "completed")
    pending = sum(1 for hw in homework_list if hw.status == "pending")
    in_progress = sum(1 for hw in homework_list if hw.status == "in_progress")
    cancelled = sum(1 for hw in homework_list if hw.status == "cancelled")
    overdue = sum(
        1 for hw in homework_list 
        if hw.status == "pending" and hw.due_date and hw.due_date < datetime.utcnow()
    )
    
    completion_rate = completed / total if total > 0 else 0.0
    
    return StudentStats(
        student_id=student_id,
        total=total,
        completed=completed,
        pending=pending,
        in_progress=in_progress,
        cancelled=cancelled,
        completion_rate=completion_rate,
        overdue=overdue
    )


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new student and link to parent.
    
    Only parents and admins can create students.
    """
    # Parents can only create students for themselves
    if current_user.role == "parent" and student_data.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only create students for yourself"
        )
    
    # Verify parent exists
    parent = await db.get(User, student_data.parent_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent not found"
        )
    
    student = Student(
        name=student_data.name,
        class_id=student_data.class_id,
        school_id=student_data.school_id,
        parent_id=student_data.parent_id
    )
    
    db.add(student)
    await db.commit()
    await db.refresh(student)
    
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: UUID,
    student_update: StudentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update student information.
    """
    student = await db.get(Student, student_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check permissions
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update fields
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "parent_id" or current_user.role == "admin":
            setattr(student, field, value)
    
    await db.commit()
    await db.refresh(student)
    
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a student.
    """
    student = await db.get(Student, student_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check permissions
    if current_user.role == "parent" and student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    await db.delete(student)
    await db.commit()
    
    return None
