# CLOUDINARY_URL=cloudinary://<your_api_key>:<your_api_secret>@dmjtks9zq

"""
class CloudDeletionOutbox(Base):
    __tablename__ = "cloud_deletion_outbox"

    id = Column(Integer, primary_key=True)
    public_id = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def delete_image(public_id: str):
    session.add(CloudDeletionOutbox(public_id=public_id))

for job in pending_jobs:
    cloudinary.uploader.destroy(job.public_id)
    session.delete(job)

"""