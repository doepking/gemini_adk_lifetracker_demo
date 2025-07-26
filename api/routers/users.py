import json
from typing import List

from fastapi import APIRouter, Request, Depends, status
from sqlalchemy.orm import Session

from gemini_adk_demo import crud, models, schemas
from gemini_adk_demo.database import get_db
from ..exceptions import APIException
from ..dependencies import get_current_user, verify_internal_api_key

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/by_email/{user_email}", response_model=schemas.User)
def get_user_by_email(user_email: str, request: Request, db: Session = Depends(get_db)):
    """
    Retrieves a user by their email address, creating one if not found.
    """
    user_name = request.headers.get("X-User-Name")
    user = crud.get_or_create_user(db, user_email=user_email, user_name=user_name)
    return user


@router.delete("/{user_id}/purge", status_code=status.HTTP_200_OK)
def purge_user(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> dict:
    """
    Deletes all data associated with a specific user.

    This is a destructive operation and should be used with caution.
    """
    return crud.purge_user_data(db, user_id=current_user.id)


# --- Task Endpoints ---
@router.get("/{user_id}/tasks", response_model=List[schemas.Task])
def read_tasks(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> List[models.Task]:
    """
    Retrieves all tasks for a specific user.
    """
    return crud.load_tasks(db, user_id=current_user.id)


@router.post(
    "/{user_id}/tasks", response_model=schemas.Task, status_code=status.HTTP_201_CREATED
)
def create_task_for_user(
    *,
    db: Session = Depends(get_db),
    task_in: schemas.TaskCreate,
    current_user: models.User = Depends(get_current_user)
) -> models.Task:
    """
    Creates a new task for the specified user.
    """
    deadline_str = task_in.deadline.isoformat() if task_in.deadline else None
    result = crud.create_tasks_tool(
        db=db,
        user=current_user,
        task_description=task_in.description,
        deadline=deadline_str,
    )
    if result.get("status") == "success":
        return result["task"]
    raise APIException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
    )


@router.put("/{user_id}/tasks", response_model=schemas.StatusResponse)
def update_tasks_for_user_bulk(
    *,
    db: Session = Depends(get_db),
    tasks_in: List[schemas.TaskUpdate],
    current_user: models.User = Depends(get_current_user)
) -> dict:
    """
    Updates a list of tasks for a user in bulk.
    """
    tasks_dict = [task.model_dump() for task in tasks_in]
    return crud.update_tasks_tool_bulk(db=db, user=current_user, tasks=tasks_dict)


@router.put("/{user_id}/tasks/{task_id}", response_model=schemas.Task)
def update_task_for_user(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    task_in: schemas.TaskUpdate,
    current_user: models.User = Depends(get_current_user)
) -> models.Task:
    """
    Updates a specific task for a user.
    """
    deadline_str = task_in.deadline.isoformat() if task_in.deadline else None
    result = crud.update_tasks_tool(
        db=db,
        user=current_user,
        task_id=task_id,
        task_description=task_in.description,
        task_status=task_in.status,
        deadline=deadline_str,
    )
    if result.get("status") == "success":
        return result["task"]
    raise APIException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
    )


# --- Text Input Endpoints ---
@router.get("/{user_id}/text_inputs", response_model=List[schemas.TextInput])
def read_text_inputs(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> List[models.TextInput]:
    """
    Retrieves all text input logs for a specific user.
    """
    return crud.load_input_log(db, user_id=current_user.id)


@router.post(
    "/{user_id}/text_inputs",
    response_model=schemas.TextInput,
    status_code=status.HTTP_201_CREATED,
)
def create_text_input_for_user(
    *,
    db: Session = Depends(get_db),
    text_input_in: schemas.TextInputCreate,
    current_user: models.User = Depends(get_current_user)
) -> models.TextInput:
    """
    Creates a new text input log for the specified user.
    """
    result = crud.add_log_entry_tool(
        db=db,
        text_input=text_input_in.content,
        user=current_user,
        category_suggestion=text_input_in.category,
    )
    if result.get("status") == "success":
        return result["log_entry"]
    raise APIException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
    )


@router.put("/{user_id}/text_inputs", response_model=schemas.StatusResponse)
def update_text_inputs_for_user(
    *,
    db: Session = Depends(get_db),
    text_inputs_in: List[schemas.TextInputUpdate],
    current_user: models.User = Depends(get_current_user)
) -> dict:
    """
    Updates a list of text input logs for a user.
    """
    return crud.update_input_log(db=db, user=current_user, log_list=text_inputs_in)


# --- Background Info Endpoints ---
@router.get("/{user_id}/background_info", response_model=schemas.BackgroundInfo)
def read_background_info(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> models.BackgroundInfo:
    """
    Retrieves the background information for a specific user.
    """
    return crud.load_background_info(db, user_id=current_user.id)


@router.put("/{user_id}/background_info", response_model=schemas.BackgroundInfoResponse)
def update_background_info_for_user(
    *,
    db: Session = Depends(get_db),
    background_info_in: schemas.BackgroundInfoCreate,
    current_user: models.User = Depends(get_current_user)
) -> dict:
    """
    Updates the background information for a specific user.
    """
    result = crud.update_background_info_tool(
        db=db,
        background_update_json=json.dumps(background_info_in.content),
        user=current_user,
        replace=True,
    )
    if result.get("status") == "success":
        return result
    raise APIException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
    )
