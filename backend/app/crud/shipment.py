from sqlalchemy.orm import Session
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate


def create_shipment(db: Session, shipment: ShipmentCreate):
    db_shipment = Shipment(**shipment.model_dump())
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    return db_shipment


def get_shipments(db: Session):
    return db.query(Shipment).order_by(Shipment.created_at.asc(), Shipment.tracking_number.asc()).all()


def get_shipment(db: Session, shipment_id):
    return (
        db.query(Shipment)
        .filter(Shipment.shipment_id == shipment_id)
        .first()
    )


def update_shipment(
    db: Session,
    shipment_id,
    shipment: ShipmentUpdate
):
    db_shipment = get_shipment(db, shipment_id)

    if not db_shipment:
        return None

    update_data = shipment.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_shipment, key, value)

    db.commit()
    db.refresh(db_shipment)

    return db_shipment


def delete_shipment(db: Session, shipment_id):
    db_shipment = get_shipment(db, shipment_id)

    if not db_shipment:
        return None

    db.delete(db_shipment)
    db.commit()

    return db_shipment
