from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripUpdate


def create_trip(db: Session, trip: TripCreate):
    db_trip = Trip(**trip.model_dump())
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


def get_trips(db: Session):
    return db.query(Trip).order_by(Trip.start_time.asc(), Trip.trip_id.asc()).all()


def get_trip(db: Session, trip_id):
    return (
        db.query(Trip)
        .filter(Trip.trip_id == trip_id)
        .first()
    )


def update_trip(db: Session, trip_id, trip: TripUpdate):
    db_trip = get_trip(db, trip_id)

    if not db_trip:
        return None

    update_data = trip.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_trip, key, value)

    db.commit()
    db.refresh(db_trip)

    return db_trip


def delete_trip(db: Session, trip_id):
    db_trip = get_trip(db, trip_id)

    if not db_trip:
        return None

    db.delete(db_trip)
    db.commit()

    return db_trip
