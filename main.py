from typing import Union

from fastapi import FastAPI, Request, Form
from pydantic import BaseModel
from typing import Annotated

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship

class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    value: float

class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_name: str = Field(index=True)
    client_email: str = Field(index=True)
    product_id: int | None = Field(default=None, foreign_key="product.id")
    suggar: bool
    delivery_time: int = Field(default=0)
    status: int = Field(default=0)
    product: Product | None = Relationship()

def get_session():
    with Session(engine) as session:
        yield session

class StrengthCoffee:
    values = ['Fraco', 'Médio', 'Forte']

    @staticmethod
    def get(index, default=None):
        if index < 0 or index >= len(StrengthCoffee.values):
            return default

        return StrengthCoffee.values[index]
    
class OrderStatus(object):
    values = [
        "Pedido Confirmado",
        "Pedido Pendente",
        "Pedido Entregue"
    ]

    @staticmethod
    def get(index, default=None):
        if index < 0 or index >= len(OrderStatus.values):
            return default

        return OrderStatus.values[index]


SessionDep = Annotated[Session, Depends(get_session)]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()



@app.post("/products")
def insert_product(product: Product, session: SessionDep) -> Product:
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@app.get("/products")
def list_products(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[Product]:
    products = session.exec(select(Product).offset(offset).limit(limit)).all()
    return products

@app.get("/products/{product_id}")
def get_product(product_id: int, session: SessionDep) -> Product:
    product = session.get(Product, product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product

@app.post("/orders")
def create_order(order: Order, session: SessionDep) -> Order:
    # Pedido Confirmado
    order.status = 0
    order.delivery_time = 30

    session.add(order)
    session.commit()
    session.refresh(order)
    return order

def response_order(order: Order) -> dict:
    return {
        "id": order.id,
        "client_name": order.client_name,
        "product_id": order.product_id,
        "product_name": order.product.name,
        "sugar_level": order.sugar_level,
        "strength": StrengthCoffee.get(order.strength, ""),
        "syrup": order.syrup,
        "value": order.product.value,
        "delivery_time": order.delivery_time,
        "status": OrderStatus.get(order.status, "")
    }


def response_orders(orders: list[Order]) -> list[dict]:
    ret = []
    for order in orders:
        ret.append(response_order(order))

    return ret

@app.get("/orders")
def list_orders(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[Order]:
    orders = session.exec(select(Order).offset(offset).limit(limit)).all()

    return response_orders(orders)


@app.get("/orders/{order_id}")
def get_order(order_id: int, session: SessionDep) -> dict:
    order = session.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return response_order(order)


class OrderPatch(BaseModel):
    id: int

@app.patch("/orders/{order_id}/status")
def update_order_status(status: OrderPatch, order_id: int, session: SessionDep):
    order = session.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if status.id != order.status and OrderStatus.get(status.id, None) != None:
        order.status = status.id
        session.add(order)
        session.commit()
        session.refresh(order)

    return response_order(order)

@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100):
    products = session.exec(select(Product).offset(offset).limit(limit)).all()

    return templates.TemplateResponse(
        request=request, name="index.html", context={"products": products, 'order_status': 'Seu pedido ainda não foi realizado.'}
    )


@app.post("/", response_class=HTMLResponse)
def create_order_page(order: Annotated[Order, Form()], request: Request, session: SessionDep) -> Order:
    # Pedido Confirmado
    order.status = 0
    order.delivery_time = 30

    products = session.exec(select(Product)).all()

    if order.suggar == 'on':
        order.suggar = True
    else:
        order.suggar = False

    session.add(order)
    session.commit()
    session.refresh(order)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"products": products, 'order_status': OrderStatus.get(order.status)}
    )
