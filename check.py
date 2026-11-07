import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

ids = [m.id for m in client.models.list().data if "whisper" in m.id]
print(ids)