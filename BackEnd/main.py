from fastapi import FastAPI
from database.db import supabase

app = FastAPI()

@app.get("/")
def read_root():
    response = supabase.table("customer").select("*").execute()
    return response.data
