from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI,Request,status, Depends
from fastapi.middleware.cors import CORSMiddleware
from db.init_db import init_db,create_super_admin
from apis.routers import router as api_router
from domains.auth.models.users import User
from fastapi.responses import JSONResponse
from db.init_models import create_tables
from config.settings import settings
from db.session import SessionLocal
from sqlalchemy.orm import Session
from db.session import get_db
from datetime import datetime
import requests
import uvicorn
import json
import os





## adding our api routes 
def include(app):
    app.include_router(api_router)



def initial_data_insert():
   
    db = SessionLocal()
    try:
        init_db(db)
        create_super_admin(db)
    finally:
        db.close()


    


def start_application():
    app = FastAPI(docs_url="/", title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
    app.add_middleware(
    CORSMiddleware,
    allow_origins= settings.SET_NEW_ORIGIN,
    allow_credentials=True,    
    allow_methods=["*"],
    allow_headers=["*"]
    )
    include(app)
    create_tables()
    initial_data_insert()
    return app
app = start_application()





# Custom error handling middleware
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_message = "Validation error occurred"
    # Optionally, you can log the error or perform additional actions here
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": error_message+f"{exc}"})



# Generic error handler for all other exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    error_message = "An unexpected error occurred:\n"
    # Optionally, you can log the error or perform additional actions here
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": error_message+f"{exc}"})





@app.exception_handler(json.JSONDecodeError)
async def json_decode_error_handler(request: Request, exc: json.JSONDecodeError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Configuration must be a valid JSON object"},
    )






class IntruderDetectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db: Session = Depends(get_db)):
        super().__init__(app)
        self.db = db
    
    async def intruder_info(request: Request):
        #intruder_list = []
        client_ip = request.client.host
        headers = request.headers
        user_agent = headers.get("User-Agent")
        mac_address = headers.get("X-MAC-Address")  # Custom header for MAC Address
        location = requests.get(f"https://ipinfo.io/{client_ip}/geo").json()

        intruder_info = {
            "ip_address": client_ip,
            "mac_address": mac_address,
            "user_agent": user_agent,
            "location": location,
        }
        print("intruder info dict: ", intruder_info)
        settings.intruder_list.append(intruder_info)
        print(f"Intruder detected: {intruder_info}")

        return intruder_info


    async def log_intruder_info(ip_addr: str, mac_addr: str, user_agent: str, location: str):
        # Get current date to create or append to the log file
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file_name = f"intruder_log_{current_date}.txt"
        log_directory = "security/logs/"

        os.makedirs(log_directory, exist_ok=True)
        

        # Check if the log file exists
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        
        log_filepath = os.path.join(log_directory, log_file_name)
        

        # Create log entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{ip_addr} | {mac_addr} | {user_agent} | {location} | {timestamp}"

        # Check if the log file already exists
        if os.path.exists(log_filepath):
            with open(log_filepath, 'a') as file:
                file.write("================================================================================\n")
                file.write(log_entry + "\n")
        else:
            with open(log_file_name, 'w') as file:
                file.write("IP Addr | Mac Addr | User Agent | location | Timestamp\n")
                file.write(log_entry + "\n")

        return log_filepath

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        print("response in middleware: ", response)
        # Example of handling rate limit exceeded and locking accounts
        if response.status_code == 429:  # Too Many Requests
            username = request.headers.get("X-Username")
            print("\nusername in middleware: ", username)
            if username:
                user = self.db.query(User).filter(User.username == username).first()
                if user:
                    print("user in middleware: ", user)
                    user.lock_account(lock_time_minutes=10)
                    self.db.commit()

        return response

#app.middleware("http")(IntruderDetectionMiddleware())
app.add_middleware(IntruderDetectionMiddleware)



if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8080, log_level="info", reload = True)
    print("running")