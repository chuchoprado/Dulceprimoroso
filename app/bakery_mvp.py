from __future__ import annotations

import os
from typing import Dict, List

import httpx
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pint import UnitRegistry

app = FastAPI(title="DulcePrimoroso MVP API", version="0.1.0")
ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)


# --------- Recetario base ---------
CLASSIC_DESSERTS: Dict[str, dict] = {
    "tiramisu": {
        "name": "Tiramisú clásico",
        "servings": 8,
        "ingredients": [
            {"name": "Queso mascarpone", "qty": 500, "unit": "gram"},
            {"name": "Huevos", "qty": 4, "unit": "count"},
            {"name": "Azúcar", "qty": 120, "unit": "gram"},
            {"name": "Café espresso", "qty": 300, "unit": "milliliter"},
            {"name": "Bizcochos de soletilla", "qty": 250, "unit": "gram"},
        ],
    },
    "chocolate_cake": {
        "name": "Pastel de chocolate húmedo",
        "servings": 12,
        "ingredients": [
            {"name": "Harina", "qty": 300, "unit": "gram"},
            {"name": "Cacao", "qty": 80, "unit": "gram"},
            {"name": "Azúcar", "qty": 350, "unit": "gram"},
            {"name": "Huevos", "qty": 4, "unit": "count"},
            {"name": "Mantequilla", "qty": 200, "unit": "gram"},
        ],
    },
}


class IngredientCost(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    unit: str
    unit_cost: float = Field(gt=0, description="Costo por unidad en moneda base")


class CostRequest(BaseModel):
    ingredients: List[IngredientCost]
    labor_cost: float = 0
    overhead_cost: float = 0
    margin_percent: float = Field(default=30, ge=0, le=95)
    base_currency: str = "USD"
    target_currency: str = "USD"


class ConvertRequest(BaseModel):
    value: float
    from_unit: str
    to_unit: str


class ChatRequest(BaseModel):
    question: str


@app.get("/recipes")
async def list_recipes():
    return {"recipes": CLASSIC_DESSERTS}


async def fx_convert(amount: float, base_currency: str, target_currency: str) -> float:
    if base_currency.upper() == target_currency.upper():
        return amount

    url = f"https://api.frankfurter.app/latest?amount={amount}&from={base_currency.upper()}&to={target_currency.upper()}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="No se pudo convertir la moneda")
        data = r.json()
    try:
        return float(data["rates"][target_currency.upper()])
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Respuesta inválida del servicio FX") from exc


@app.post("/costs")
async def calculate_costs(payload: CostRequest):
    ingredients_total = sum(i.quantity * i.unit_cost for i in payload.ingredients)
    production_cost = ingredients_total + payload.labor_cost + payload.overhead_cost
    final_price = production_cost / (1 - payload.margin_percent / 100)

    converted_cost = await fx_convert(production_cost, payload.base_currency, payload.target_currency)
    converted_price = await fx_convert(final_price, payload.base_currency, payload.target_currency)

    return {
        "production_cost": round(converted_cost, 2),
        "suggested_price": round(converted_price, 2),
        "currency": payload.target_currency.upper(),
        "margin_percent": payload.margin_percent,
    }


@app.post("/convert")
async def convert_units(payload: ConvertRequest):
    try:
        q = payload.value * ureg(payload.from_unit)
        converted = q.to(payload.to_unit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Conversión inválida: {exc}") from exc

    return {
        "original": f"{payload.value} {payload.from_unit}",
        "converted_value": round(converted.magnitude, 4),
        "to_unit": payload.to_unit,
    }


@app.post("/chat")
async def baker_chat(payload: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Define OPENAI_API_KEY para usar el chat")

    client = AsyncOpenAI(api_key=api_key)
    response = await client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": "Eres una maestra repostera. Da respuestas prácticas, breves y seguras.",
            },
            {"role": "user", "content": payload.question},
        ],
    )
    return {"answer": response.output_text}
