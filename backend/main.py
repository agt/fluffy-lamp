from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import Integer, String, DateTime, ForeignKey, select, func
import sqlalchemy as sa
from datetime import datetime, timezone
from typing import Optional
import os
import pathlib

DATABASE_URL = "sqlite+aiosqlite:///./bulletin.db"
engine = create_async_engine(DATABASE_URL, echo=False)

STATIC_DIR = pathlib.Path(__file__).parent / "static"


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author: Mapped[str] = mapped_column(String(100), default="Anonymous")
    content: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Reaction(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    note_id: Mapped[int] = mapped_column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    emoji: Mapped[str] = mapped_column(String(10))


# Pydantic schemas
class NoteCreate(BaseModel):
    author: str = Field(default="Anonymous", max_length=100)
    content: str = Field(min_length=1, max_length=1000)


class ReactionCount(BaseModel):
    emoji: str
    count: int


class NoteOut(BaseModel):
    id: int
    author: str
    content: str
    created_at: datetime
    reactions: list[ReactionCount] = []

    model_config = {"from_attributes": True}


class ReactionCreate(BaseModel):
    emoji: str = Field(min_length=1, max_length=10)


app = FastAPI(title="Bulletin Board")

ALLOWED_EMOJIS = {"👍", "❤️", "😂", "😮", "😢", "👏", "🔥", "🎉"}


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSession(engine) as session:
        yield session


from fastapi import Depends


@app.get("/api/notes", response_model=list[NoteOut])
async def list_notes(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Note).order_by(Note.created_at.desc())
    )
    notes = result.scalars().all()

    # Fetch reaction counts for all notes
    reaction_result = await session.execute(
        select(Reaction.note_id, Reaction.emoji, func.count(Reaction.id).label("cnt"))
        .group_by(Reaction.note_id, Reaction.emoji)
    )
    reactions_map: dict[int, list[ReactionCount]] = {}
    for row in reaction_result:
        reactions_map.setdefault(row.note_id, []).append(
            ReactionCount(emoji=row.emoji, count=row.cnt)
        )

    return [
        NoteOut(
            id=n.id,
            author=n.author,
            content=n.content,
            created_at=n.created_at,
            reactions=reactions_map.get(n.id, []),
        )
        for n in notes
    ]


@app.post("/api/notes", response_model=NoteOut, status_code=201)
async def create_note(data: NoteCreate, session: AsyncSession = Depends(get_session)):
    note = Note(author=data.author or "Anonymous", content=data.content)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return NoteOut(id=note.id, author=note.author, content=note.content, created_at=note.created_at, reactions=[])


@app.post("/api/notes/{note_id}/reactions", status_code=204)
async def add_reaction(note_id: int, data: ReactionCreate, session: AsyncSession = Depends(get_session)):
    if data.emoji not in ALLOWED_EMOJIS:
        raise HTTPException(status_code=400, detail="Emoji not allowed")
    result = await session.execute(select(Note).where(Note.id == note_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Note not found")
    reaction = Reaction(note_id=note_id, emoji=data.emoji)
    session.add(reaction)
    await session.commit()


@app.delete("/api/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await session.delete(note)
    await session.commit()


# Serve Vue SPA — must be after API routes
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = STATIC_DIR / "index.html"
        return FileResponse(index)
