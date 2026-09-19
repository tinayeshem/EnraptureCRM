import os 
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url : str = os.environ.get("supaUrl")
key : str = os.environ.get("supaApi")

supabase: Client = create_client(url, key)


def get_service_client() -> Client:
    """Returns a fresh Supabase client with pure service_role credentials."""
    return create_client(url, key)