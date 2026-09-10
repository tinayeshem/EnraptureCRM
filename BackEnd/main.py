from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, status
from database.db import supabase
from Model import (
    Customer,
    CustomerCreate,
    Booking,
    BookingCreate,
    RoomBooking,
    CampBooking,
    Catering,
    ShuttleBooking,
    Review,
    BoatBooking,
)

app = FastAPI(
    title="Enrapture CRM API",
    description="CRM API with FastAPI, Supabase, and Pydantic models",
    version="1.0.0",
)


def get_next_id(table_name: str, id_column: str) -> int:
    """Helper to auto-generate the next ID for tables without Postgres serial/identity defaults."""
    res = (
        supabase.table(table_name)
        .select(id_column)
        .order(id_column, desc=True)
        .limit(1)
        .execute()
    )
    if res.data and res.data[0].get(id_column) is not None:
        return res.data[0][id_column] + 1
    return 1


@app.get("/", tags=["Root"])
def read_root():
    response = supabase.table("customer").select("*").execute()
    return response.data


# --- Customer ---
@app.post("/customer", tags=["Customer"], status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerCreate):
    first_name = customer.first_name.strip()
    last_name = customer.last_name.strip()

    # Deny request if a customer with matching name and surname already exists
    existing = (
        supabase.table("customer")
        .select("customer_id")
        .ilike("first_name", first_name)
        .ilike("last_name", last_name)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Customer with name '{first_name} {last_name}' already exists.",
        )

    try:
        payload = customer.model_dump(mode="json", exclude_none=True)
        payload["first_name"] = first_name
        payload["last_name"] = last_name

        # customer_id is assigned automatically by the database sequence
        if not payload.get("created_at"):
            payload["created_at"] = datetime.now(timezone.utc).isoformat()

        response = supabase.table("customer").insert(payload).execute()
        return {
            "message": "Customer created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create customer: {str(e)}",
        )


# --- Booking ---
@app.post("/booking", tags=["Booking"], status_code=status.HTTP_201_CREATED)
def create_booking(booking: BookingCreate):
    # Verify customer exists
    customer_check = (
        supabase.table("customer")
        .select("customer_id")
        .eq("customer_id", booking.customer_id)
        .execute()
    )
    if not customer_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {booking.customer_id} does not exist.",
        )

    try:
        payload = booking.model_dump(mode="json", exclude_none=True)
        # Automatically assign the next booking_id
        payload["booking_id"] = get_next_id("booking", "booking_id")

        if not payload.get("booking_date"):
            payload["booking_date"] = datetime.now(timezone.utc).isoformat()

        if "total_price" in payload:
            payload["total_price"] = float(payload["total_price"])

        response = supabase.table("booking").insert(payload).execute()
        return {
            "message": "Booking created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create booking: {str(e)}",
        )


# --- Room Booking ---
@app.post("/room-booking", tags=["Room Booking"], status_code=status.HTTP_201_CREATED)
def create_room_booking(room_booking: RoomBooking):
    try:
        payload = room_booking.model_dump(mode="json", exclude_none=True)
        if payload.get("room_booking_id") in (None, 0):
            payload["room_booking_id"] = get_next_id("room_booking", "room_booking_id")

        response = supabase.table("room_booking").insert(payload).execute()
        return {
            "message": "Room booking created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create room booking: {str(e)}",
        )


# --- Camp Booking ---
@app.post("/camp-booking", tags=["Camp Booking"], status_code=status.HTTP_201_CREATED)
def create_camp_booking(camp_booking: CampBooking):
    try:
        payload = camp_booking.model_dump(mode="json", exclude_none=True)
        if payload.get("camp_booking_id") in (None, 0):
            payload["camp_booking_id"] = get_next_id("camping_booking", "camp_booking_id")

        response = supabase.table("camping_booking").insert(payload).execute()
        return {
            "message": "Camp booking created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create camp booking: {str(e)}",
        )


# --- Catering ---
@app.post("/catering", tags=["Catering"], status_code=status.HTTP_201_CREATED)
def create_catering(catering: Catering):
    try:
        payload = catering.model_dump(mode="json", exclude_none=True)
        if payload.get("order_id") in (None, 0):
            payload["order_id"] = get_next_id("catering", "order_id")

        response = supabase.table("catering").insert(payload).execute()
        return {
            "message": "Catering order created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create catering order: {str(e)}",
        )


# --- Shuttle Booking ---
@app.post("/shuttle-booking", tags=["Shuttle Booking"], status_code=status.HTTP_201_CREATED)
def create_shuttle_booking(shuttle_booking: ShuttleBooking):
    try:
        payload = shuttle_booking.model_dump(mode="json", exclude_none=True)
        if payload.get("shuttle_booking_id") in (None, 0):
            payload["shuttle_booking_id"] = get_next_id("shuttle_booking", "shuttle_booking_id")

        response = supabase.table("shuttle_booking").insert(payload).execute()
        return {
            "message": "Shuttle booking created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create shuttle booking: {str(e)}",
        )


# --- Review ---
@app.post("/review", tags=["Review"], status_code=status.HTTP_201_CREATED)
def create_review(review: Review):
    try:
        payload = review.model_dump(mode="json", exclude_none=True)
        if payload.get("review_id") in (None, 0):
            payload["review_id"] = get_next_id("review", "review_id")
        if not payload.get("created_at"):
            payload["created_at"] = datetime.now(timezone.utc).isoformat()

        response = supabase.table("review").insert(payload).execute()
        return {
            "message": "Review created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create review: {str(e)}",
        )


# --- Boat Booking ---
@app.post("/boat-booking", tags=["Boat Booking"], status_code=status.HTTP_201_CREATED)
def create_boat_booking(boat_booking: BoatBooking):
    try:
        payload = boat_booking.model_dump(mode="json", exclude_none=True)
        if payload.get("boat_booking_id") in (None, 0):
            payload["boat_booking_id"] = get_next_id("boat_booking", "boat_booking_id")

        response = supabase.table("boat_booking").insert(payload).execute()
        return {
            "message": "Boat booking created successfully",
            "data": response.data[0] if response.data else payload,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create boat booking: {str(e)}",
        )
