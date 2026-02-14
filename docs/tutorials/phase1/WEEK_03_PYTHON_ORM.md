# Week 3: Python ORM & API Integration

**Phase 1 Tutorial Series**  
**Duration**: ~8 hours  
**Prerequisites**: Weeks 1-2 complete, Python basics

---

## Overview

This week covers:
- **Module 5**: Python ORM with SQLAlchemy (4 hours)
- **Module 6**: API Integration (4 hours)

### Weekly Goals
- [ ] Understand SQLAlchemy ORM concepts
- [ ] Use Python to interact with the database
- [ ] Understand the repository pattern
- [ ] Connect API endpoints to database operations

---

## Day 1-2: Module 5 — SQLAlchemy ORM

### Study Materials

Read the complete module:
```
docs/database/curriculum/05-MODULE-SQLALCHEMY-ORM.md
```

Also review these project files:
```
apps/api/app/db/models.py
apps/api/app/db/enums.py
apps/api/app/db/session.py
```

### Key Concepts to Master

#### 1. What is an ORM?

**ORM** = Object-Relational Mapping

Instead of writing SQL:
```sql
SELECT * FROM video WHERE split = 'train';
```

You write Python:
```python
videos = session.query(Video).filter(Video.split == 'train').all()
```

**Benefits**:
- Type safety and IDE autocomplete
- Database-agnostic code
- Easier testing with mocks
- Automatic SQL injection prevention

#### 2. SQLAlchemy Models

From `apps/api/app/db/models.py`:

```python
from sqlalchemy import Column, String, Numeric, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid

class Video(Base):
    __tablename__ = "video"
    
    video_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String(500), nullable=False)
    split = Column(String(20), nullable=False, default='temp')
    label = Column(String(20), nullable=True)
    sha256 = Column(String(64), nullable=True)
    duration_sec = Column(Numeric(10, 2), nullable=True)
    width = Column(BigInteger, nullable=True)
    height = Column(BigInteger, nullable=True)
    fps = Column(Numeric(5, 2), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    training_selections = relationship("TrainingSelection", back_populates="video")
    promotion_logs = relationship("PromotionLog", back_populates="video")
```

#### 3. Python Enums

From `apps/api/app/db/enums.py`:

```python
from enum import Enum

class VideoSplit(str, Enum):
    TEMP = "temp"
    DATASET_ALL = "dataset_all"
    TRAIN = "train"
    TEST = "test"
    PURGED = "purged"

class EmotionLabel(str, Enum):
    ANGER = "anger"
    CONTEMPT = "contempt"
    DISGUST = "disgust"
    FEAR = "fear"
    HAPPINESS = "happiness"
    NEUTRAL = "neutral"
    SADNESS = "sadness"
    SURPRISE = "surprise"
```

#### 4. Database Sessions

From `apps/api/app/db/session.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

#### 5. CRUD Operations with SQLAlchemy

**Create**:
```python
async def create_video(db: AsyncSession, file_path: str) -> Video:
    video = Video(file_path=file_path, split=VideoSplit.TEMP)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video
```

**Read**:
```python
async def get_video(db: AsyncSession, video_id: UUID) -> Video | None:
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    return result.scalar_one_or_none()

async def list_videos(db: AsyncSession, split: VideoSplit = None) -> list[Video]:
    query = select(Video)
    if split:
        query = query.where(Video.split == split)
    result = await db.execute(query)
    return result.scalars().all()
```

**Update**:
```python
async def update_video_label(
    db: AsyncSession, 
    video_id: UUID, 
    label: EmotionLabel
) -> Video:
    video = await get_video(db, video_id)
    if not video:
        raise ValueError(f"Video not found: {video_id}")
    
    video.label = label
    video.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(video)
    return video
```

**Delete**:
```python
async def delete_video(db: AsyncSession, video_id: UUID) -> bool:
    video = await get_video(db, video_id)
    if not video:
        return False
    
    await db.delete(video)
    await db.commit()
    return True
```

### Exercises

1. **Create a test script** (`test_orm.py`):
   ```python
   import asyncio
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from sqlalchemy import select
   
   # Import your models
   from apps.api.app.db.models import Video
   from apps.api.app.db.enums import VideoSplit
   
   DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"
   
   async def main():
       engine = create_async_engine(DATABASE_URL)
       async_session = sessionmaker(engine, class_=AsyncSession)
       
       async with async_session() as session:
           # List all videos
           result = await session.execute(select(Video).limit(5))
           videos = result.scalars().all()
           
           for video in videos:
               print(f"{video.video_id}: {video.file_path} ({video.split})")
   
   asyncio.run(main())
   ```

2. **Practice queries**:
   ```python
   # Count by split
   from sqlalchemy import func
   
   result = await session.execute(
       select(Video.split, func.count(Video.video_id))
       .group_by(Video.split)
   )
   for split, count in result:
       print(f"{split}: {count}")
   
   # Find unlabeled videos
   result = await session.execute(
       select(Video).where(Video.label == None)
   )
   unlabeled = result.scalars().all()
   ```

### Checkpoint: Days 1-2
- [ ] Understand ORM concept
- [ ] Can read SQLAlchemy model definitions
- [ ] Understand async sessions
- [ ] Can write basic CRUD operations

---

## Day 3-4: Module 6 — API Integration

### Study Materials

Read the complete module:
```
docs/database/curriculum/06-MODULE-API-INTEGRATION.md
```

Also review these project files:
```
apps/api/routers/promote.py
apps/api/app/services/promote_service.py
apps/api/app/repositories/video_repository.py
```

### Key Concepts to Master

#### 1. Repository Pattern

The **repository pattern** separates data access from business logic:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Router    │────▶│   Service   │────▶│ Repository  │────▶ Database
│  (FastAPI)  │     │  (Logic)    │     │ (Data)      │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Repository** (`video_repository.py`):
```python
class VideoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, video_id: UUID) -> Video | None:
        result = await self.db.execute(
            select(Video).where(Video.video_id == video_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_split(self, split: VideoSplit) -> list[Video]:
        result = await self.db.execute(
            select(Video).where(Video.split == split)
        )
        return result.scalars().all()
    
    async def update(self, video: Video) -> Video:
        self.db.add(video)
        await self.db.commit()
        await self.db.refresh(video)
        return video
```

#### 2. Service Layer

**Service** (`promote_service.py`):
```python
class PromoteService:
    def __init__(self, video_repo: VideoRepository, log_repo: PromotionLogRepository):
        self.video_repo = video_repo
        self.log_repo = log_repo
    
    async def promote_video(
        self,
        video_id: UUID,
        label: EmotionLabel,
        user_id: str
    ) -> Video:
        # Get video
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id)
        
        # Validate current state
        if video.split != VideoSplit.TEMP:
            raise InvalidStateError(f"Video not in temp: {video.split}")
        
        # Update video
        video.split = VideoSplit.DATASET_ALL
        video.label = label
        video.updated_at = datetime.utcnow()
        
        # Save changes
        video = await self.video_repo.update(video)
        
        # Log promotion
        await self.log_repo.create(
            video_id=video_id,
            from_split=VideoSplit.TEMP,
            to_split=VideoSplit.DATASET_ALL,
            label=label,
            user_id=user_id
        )
        
        return video
```

#### 3. FastAPI Router

**Router** (`promote.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/api/v1/promote", tags=["promote"])

class PromoteRequest(BaseModel):
    video_id: UUID
    label: str
    user_id: str = "anonymous"

class PromoteResponse(BaseModel):
    video_id: UUID
    file_path: str
    split: str
    label: str

@router.post("/video", response_model=PromoteResponse)
async def promote_video(
    request: PromoteRequest,
    db: AsyncSession = Depends(get_db)
):
    video_repo = VideoRepository(db)
    log_repo = PromotionLogRepository(db)
    service = PromoteService(video_repo, log_repo)
    
    try:
        video = await service.promote_video(
            request.video_id,
            EmotionLabel(request.label),
            request.user_id
        )
        return PromoteResponse(
            video_id=video.video_id,
            file_path=video.file_path,
            split=video.split,
            label=video.label
        )
    except VideoNotFoundError:
        raise HTTPException(404, "Video not found")
    except InvalidStateError as e:
        raise HTTPException(400, str(e))
```

#### 4. Dependency Injection

FastAPI uses `Depends()` for dependency injection:

```python
from fastapi import Depends

# Database session dependency
async def get_db():
    async with async_session() as session:
        yield session

# Repository dependency
def get_video_repo(db: AsyncSession = Depends(get_db)) -> VideoRepository:
    return VideoRepository(db)

# Use in router
@router.get("/videos/{video_id}")
async def get_video(
    video_id: UUID,
    repo: VideoRepository = Depends(get_video_repo)
):
    video = await repo.get_by_id(video_id)
    if not video:
        raise HTTPException(404, "Not found")
    return video
```

### Exercises

1. **Trace a request through the layers**:
   - Start at `apps/api/routers/promote.py`
   - Follow to service layer
   - Follow to repository layer
   - Understand how data flows

2. **Create a simple endpoint**:
   ```python
   # In a new file: apps/api/routers/stats.py
   from fastapi import APIRouter, Depends
   from sqlalchemy import select, func
   from sqlalchemy.ext.asyncio import AsyncSession
   
   from ..db.models import Video
   from ..db.session import get_db
   
   router = APIRouter(prefix="/api/stats", tags=["stats"])
   
   @router.get("/counts")
   async def get_counts(db: AsyncSession = Depends(get_db)):
       result = await db.execute(
           select(Video.split, func.count(Video.video_id))
           .group_by(Video.split)
       )
       return {split: count for split, count in result}
   ```

3. **Test the endpoint**:
   ```bash
   # Start the API
   uvicorn apps.api.main:app --reload
   
   # Test with curl
   curl http://localhost:8000/api/stats/counts
   ```

### Checkpoint: Days 3-4
- [ ] Understand repository pattern
- [ ] Understand service layer
- [ ] Can trace request through layers
- [ ] Can create simple endpoints

---

## Day 5: Practice & Review

### Comprehensive Exercise

Create a complete feature: "Get Dataset Statistics"

1. **Repository** (`stats_repository.py`):
   ```python
   class StatsRepository:
       def __init__(self, db: AsyncSession):
           self.db = db
       
       async def get_split_counts(self) -> dict[str, int]:
           result = await self.db.execute(
               select(Video.split, func.count(Video.video_id))
               .group_by(Video.split)
           )
           return {split: count for split, count in result}
       
       async def get_label_counts(self) -> dict[str, int]:
           result = await self.db.execute(
               select(Video.label, func.count(Video.video_id))
               .where(Video.label != None)
               .group_by(Video.label)
           )
           return {label: count for label, count in result}
   ```

2. **Service** (`stats_service.py`):
   ```python
   class StatsService:
       def __init__(self, repo: StatsRepository):
           self.repo = repo
       
       async def get_dataset_stats(self) -> dict:
           split_counts = await self.repo.get_split_counts()
           label_counts = await self.repo.get_label_counts()
           
           total = sum(split_counts.values())
           labeled = sum(label_counts.values())
           
           return {
               "total_videos": total,
               "labeled_videos": labeled,
               "label_rate": labeled / total if total > 0 else 0,
               "by_split": split_counts,
               "by_label": label_counts,
           }
   ```

3. **Router** (`stats.py`):
   ```python
   @router.get("/dataset")
   async def get_dataset_stats(db: AsyncSession = Depends(get_db)):
       repo = StatsRepository(db)
       service = StatsService(repo)
       return await service.get_dataset_stats()
   ```

### Knowledge Check

1. What is the purpose of the repository pattern?
2. Why do we use async/await with SQLAlchemy?
3. What does `Depends(get_db)` do in FastAPI?
4. How does the service layer differ from the repository?
5. What is Pydantic used for in FastAPI?

---

## Week 3 Deliverables

| Deliverable | Status |
|-------------|--------|
| Module 5 read | [ ] |
| Module 6 read | [ ] |
| ORM queries working | [ ] |
| Repository pattern understood | [ ] |
| Simple endpoint created | [ ] |
| Comprehensive exercise complete | [ ] |

---

## Next Week

[Week 4: Migrations & Troubleshooting](WEEK_04_MIGRATIONS_TROUBLESHOOTING.md) covers:
- Database migrations with SQL and Alembic
- Common database issues and fixes
- DevOps considerations
