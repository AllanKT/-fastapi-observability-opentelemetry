import logging
from datetime import datetime

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# from .mid import MetricsMeddleware

app = FastAPI()
# app.add_middleware(MetricsMeddleware)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PessoaIn(BaseModel):
    username: str
    email: str
    senha: str


class PessoaOut(PessoaIn):
    id: int
    created_at: datetime


@app.get('/user/{user_id}')
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        logger.info('Requisitando app1')
        response = await client.get(f'http://app1:8001/user/{user_id}')

        return response.json()


@app.get('/user')
async def get_users():
    async with httpx.AsyncClient() as client:
        logger.info('Requisitando app1')
        response = await client.get('http://app1:8001/user')

    return response.json()


@app.post('/user', response_model=PessoaOut)
async def create_user(user: PessoaIn):
    async with httpx.AsyncClient() as client:
        logger.info('Requisitando app1')
        response = await client.post(
            'http://app1:8001/user', json=user.model_dump()
        )

        return response.json()