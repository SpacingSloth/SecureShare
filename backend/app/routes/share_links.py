from fastapi import APIRouter

router = APIRouter(
    prefix="/share-links",
    tags=["Share Links"]
)

@router.get("/")
async def test_route():
    return {"message": "Share links router is working"}