import asyncio
import logging
from collections.abc import Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

import boto3
import fastapi
import fastapi.middleware.cors
import fastapi.responses
import httpx
import sqlmodel
from botocore.exceptions import ClientError
from fastapi import Depends
from playwright.sync_api import sync_playwright
from pydantic_settings import BaseSettings
from sqlalchemy import DateTime

# ============================================================================
# Config
# ============================================================================


class Settings(BaseSettings):
    DB_HOST: str = ""
    DB_PORT: str = "5432"
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    CHECK_INTERVAL: int = 5
    AWS_ACCESS_KEY_ID: str | None = None  # Optional, for local dev with localstack
    AWS_SECRET_ACCESS_KEY: str | None = None  # Optional, for local dev with localstack
    AWS_ENDPOINT_URL: str = ""
    AWS_REGION: str = ""
    S3_BUCKET_NAME: str = ""


settings = Settings()

# Initialize S3 client
# Uses explicit credentials for local dev (localstack), IRSA credentials in EKS
s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    endpoint_url=settings.AWS_ENDPOINT_URL or None,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


# ============================================================================
# Database
# ============================================================================

# Construct DATABASE_URL from individual components
DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
engine = sqlmodel.create_engine(DATABASE_URL)


def migrate():
    sqlmodel.SQLModel.metadata.create_all(engine)


def get_session():
    with sqlmodel.Session(engine) as session:
        yield session


SessionDep = Annotated[sqlmodel.Session, Depends(get_session)]


# ============================================================================
# Models
# ============================================================================


class Site(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    url: str = sqlmodel.Field(unique=True, index=True)
    screenshot: str
    created_at: datetime = sqlmodel.Field(
        sa_column=sqlmodel.Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )


class HealthCheck(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    site_id: int = sqlmodel.Field(foreign_key="site.id")
    is_up: bool
    created_at: datetime = sqlmodel.Field(
        sa_column=sqlmodel.Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ============================================================================
# Lifecycle
# ============================================================================


def ensure_s3_bucket():
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        logging.info(f"S3 bucket '{settings.S3_BUCKET_NAME}' already exists")
    except ClientError:
        try:
            s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            logging.info(f"Created S3 bucket '{settings.S3_BUCKET_NAME}'")
        except ClientError as e:
            logging.error(f"Failed to create S3 bucket: {e}")


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    migrate()
    ensure_s3_bucket()
    task = asyncio.create_task(check_sites())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ============================================================================
# App & Routes
# ============================================================================

app = fastapi.FastAPI(lifespan=lifespan)
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/livez", response_class=fastapi.responses.PlainTextResponse)
async def livez():
    return "ok"


@app.get("/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Retrieve screenshot from S3"""
    try:
        response = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=filename)
        return fastapi.responses.StreamingResponse(
            response["Body"], media_type="image/png"
        )
    except ClientError as e:
        raise fastapi.HTTPException(status_code=404, detail="Screenshot not found")


@app.get("/sites")
def list_sites(session: SessionDep) -> Sequence[Site]:
    query = sqlmodel.select(Site)
    instances = session.exec(query).all()
    return instances


class SiteCreate(Site, table=False):
    screenshot: str = sqlmodel.Field(default="", exclude=True)


@app.post("/sites")
def create_site(
    session: SessionDep,
    input: Site,
    background_tasks: fastapi.BackgroundTasks,
) -> Site:
    instance = Site.model_validate(input)
    session.add(instance)
    session.commit()
    session.refresh(instance)

    background_tasks.add_task(capture_screenshot, instance.id)

    return instance


@app.get("/sites/{site_id}/healthchecks")
def list_healthchecks(
    session: SessionDep, site_id: int, limit: int = 10
) -> Sequence[HealthCheck]:
    query = sqlmodel.select(Site).where(Site.id == site_id)
    site = session.exec(query).one()

    statement = (
        sqlmodel.select(HealthCheck)
        .where(HealthCheck.site_id == site.id)
        .order_by(HealthCheck.created_at.desc())
        .limit(limit)
    )
    instances = session.exec(statement).all()
    return instances


@app.post("/create-drift")
async def create_drift():
    """Intentionally modify RDS instance to create infrastructure drift"""
    try:
        # Initialize RDS client
        rds_client = boto3.client(
            "rds",
            region_name=settings.AWS_REGION,
            endpoint_url=settings.AWS_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        # Find the RDS instance by matching the DB host
        response = rds_client.describe_db_instances()
        instance = None
        for db_instance in response["DBInstances"]:
            if settings.DB_HOST in db_instance["Endpoint"]["Address"]:
                instance = db_instance
                break

        if not instance:
            return {
                "status": "error",
                "message": f"RDS instance not found for host: {settings.DB_HOST}",
            }

        instance_id = instance["DBInstanceIdentifier"]
        current_storage = instance["AllocatedStorage"]
        current_max_storage = instance.get("MaxAllocatedStorage", current_storage)
        instance_arn = instance["DBInstanceArn"]

        # Increment max allocated storage by 1 GB
        new_max_storage = current_max_storage + 1
        rds_client.modify_db_instance(
            DBInstanceIdentifier=instance_id,
            MaxAllocatedStorage=new_max_storage,
            ApplyImmediately=True,
        )

        # Add drift tags
        drift_timestamp = datetime.now(timezone.utc).isoformat()
        rds_client.add_tags_to_resource(
            ResourceName=instance_arn,
            Tags=[
                {"Key": "DriftTest", "Value": drift_timestamp},
            ],
        )

        logging.info(f"Created drift on RDS instance {instance_id}")

        return {
            "status": "success",
            "message": "Infrastructure drift created successfully",
        }

    except ClientError as e:
        error_msg = f"AWS ClientError: {e.response['Error']['Message']}"
        logging.error(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.exception("Failed to create drift")
        return {"status": "error", "message": error_msg}


# ============================================================================
# Jobs
# ============================================================================


def capture_screenshot(site_id: int) -> None:
    # Lookup site
    with sqlmodel.Session(engine) as session:
        try:
            query = sqlmodel.select(Site).where(Site.id == site_id)
            site = session.exec(query).one()
        except Exception:
            logging.exception(f"Failed to retrieve site with id: {site_id}")
            return

    # Take screenshot
    filename = f"site_{site.id}.png"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(site.url, timeout=5000)
            screenshot_bytes = page.screenshot()
            browser.close()

        # Upload to S3
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=filename,
            Body=screenshot_bytes,
            ContentType="image/png",
        )
        logging.info(f"Uploaded screenshot to S3: {filename}")
    except Exception as e:
        logging.exception(f"Failed to capture screenshot for {site.url}")
        return None

    # Update site with screenshot path
    with sqlmodel.Session(engine) as session:
        site.screenshot = f"/screenshots/{filename}"
        session.add(site)
        session.commit()


async def check_sites():
    logging.info("Starting periodic site checks...")
    while True:
        logging.info("Checking sites...")
        with sqlmodel.Session(engine) as session:
            query = sqlmodel.select(Site)
            sites = session.exec(query).all()

        for site in sites:
            asyncio.create_task(check_site(site))

        await asyncio.sleep(settings.CHECK_INTERVAL)


async def check_site(site: Site):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.head(site.url)
            is_up = response.status_code < 500
        except Exception:
            is_up = False

    assert site.id
    healthcheck = HealthCheck(site_id=site.id, is_up=is_up)
    with sqlmodel.Session(engine) as session:
        session.add(healthcheck)
        session.commit()
