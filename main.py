from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Field, Session, create_engine, select


# Building Model
class Note(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    title: str = Field(index=True)
    content: str
    is_done: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class NoteCreate(SQLModel):
    title: str
    content: str


class NoteUpdate(SQLModel):
    title: Optional[str]
    content: Optional[str]
    is_done: Optional[bool]


# Setup database engine
connect_args = {"check_same_thread": False}
engine = create_engine("sqlite:///./note.db", echo=True, connect_args=connect_args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="FastAPI + SQLModel",
    description="FastAPI backend CRUD using SQLModel",
    lifespan=lifespan,
)


# Get database session
def get_session():
    with Session(engine) as session:
        yield session


# Buidling routes


# Creating a new Note
@app.post("/note", response_model=Note)
def create(payload: NoteCreate, session: Session = Depends(get_session)):
    note = Note.model_validate(payload)

    session.add(note)
    session.commit()
    session.refresh(note)

    return note


# Get all Notes
@app.get("notes", response_model=List[Note])
def get_notes(is_done: Optional[bool], session: Session = Depends(get_session)):
    note = select(Note)

    if is_done is not None:
        note = note.where(Note.is_done == is_done)

    note = note.order_by(Note.created_at.desc())

    return session.exec(note).all()


# Get a single note
@app.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: int, session: Session = Depends(get_session)):
    note = session.get(Note, note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    return note


# Update note
@app.put("/notes/{note_id}", response_model=Note)
def update_note(
    note_id: int, payload: NoteUpdate, session: Session = Depends(get_session)
):
    note = session.exec(select(Note).where(Note.id == note_id)).one()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    updated_data = payload.model_dump(exclude_unset=True)

    for key, value in updated_data.items():
        setattr(note, key, value)

    session.add(note)
    session.commit()
    session.refresh(note)

    return note


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", port=4000, reload=True)
