from sqlalchemy import create_engine, Column, String, Integer, or_ , func 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel as PydanticBaseModel
from fastapi.middleware.cors import CORSMiddleware
from operator import itemgetter
from typing import Dict
from itertools import groupby
from collections import defaultdict



app = FastAPI(title='News Pictures')

# Configurer le middleware CORS
origins = ["http://localhost:3000"]  # Remplacez cela par l'URL de votre application React

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Création de la connexion à la base de données
engine = create_engine('sqlite:///gallery.db')
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class ImageDataDB(Base):
    __tablename__ = 'galleryTable'
    
    id = Column(Integer, primary_key=True)
    media = Column(String)
    sectionTitle = Column(String)
    pubDate = Column(String)
    pageUrl = Column(String)
    caption = Column(String)
    location = Column(String)
    author = Column(String)
    credits = Column(String)
    picture = Column(String)
    rates = Column(Integer, default=0,  nullable=True)
    
class ImageData(PydanticBaseModel):
    media: Optional[str]
    sectionTitle: Optional[str]
    pubDate: Optional[str]
    pageUrl: Optional[str]
    caption: Optional[str]
    location: Optional[str]
    author: Optional[str]
    credits: Optional[str]
    picture: Optional[str]
    rates: Optional[int] = 0
    
    class Config:
        orm_mode = True
    
@app.get("/")
async def count_all_images():
    total = session.query(func.count()).select_from(ImageDataDB).scalar()
    return f"Total number of images: {total}"

# Fonction de recherche par crédit utilisant SQLAlchemy
@app.get("/images/credits/{credit}", response_model=List[ImageData])
async def get_images_by_credit(credit: str):
    # Convertir le terme de recherche en minuscules
    credit_lower = credit.lower()

    # Récupérer les données correspondantes à un crédit donné (insensible à la casse)
    images = session.query(ImageDataDB).filter(
        or_(
            func.lower(ImageDataDB.credits).ilike(credit_lower),  # Crédit exact
            func.lower(ImageDataDB.credits).ilike(f"{credit_lower}/%"),  # Crédit avec préfixe
            func.lower(ImageDataDB.credits).ilike(f"%/{credit_lower}"),  # Crédit avec suffixe
            func.lower(ImageDataDB.credits).ilike(f"%/{credit_lower}/%")  # Crédit avec préfixe et suffixe
        )
    ).all()
    image_data_list = [image.__dict__ for image in images] # Convertir les objets ImageDataDB en dictionnaires
    image_data_list = [{k: v for k, v in image_data.items() if k != '_sa_instance_state'} for image_data in image_data_list]# Supprimer la clé '_sa_instance_state' qui n'est pas nécessaire
    return image_data_list


def count_images_by_credits():
    count = session.query(ImageDataDB.credits, func.count(ImageDataDB.id)).group_by(ImageDataDB.credits).all()# Utilisation de la fonction `func.count` de SQLAlchemy pour compter les éléments
    count_dict = {credit: count for credit, count in count}# Création d'un dictionnaire pour stocker le compte des éléments par crédits
    return count_dict 



@app.get("/images/count")
async def count_images():
    count_dict = count_images_by_credits()
    return count_dict


@app.get("/images/all_id")
async def get_all_images_by_id():    
    images = session.query(ImageDataDB).all()
    images_dict = [dict(image.__dict__) for image in images]
    # Vérification des images avec "picture" null
    filtered_images = [image for image in images_dict if image.get("picture") is not None and image.get("caption") is not None]
    # Vérification si des images ont été filtrées
    if not filtered_images:
        raise HTTPException(status_code=404, detail="Aucune image disponible.")  
    sorted_images = sorted(filtered_images, key=itemgetter('id'), reverse=True)
    return sorted_images


@app.get("/images/all_date")
async def get_all_images_by_date():    
    images = session.query(ImageDataDB).all()
    images_dict = [dict(image.__dict__) for image in images]
    # Vérification des images avec "picture" null
    filtered_images = [image for image in images_dict if image.get("picture") is not None and image.get("caption") is not None]
    # Vérification si des images ont été filtrées
    if not filtered_images:
        raise HTTPException(status_code=404, detail="Aucune image disponible.")  
    sorted_images = sorted(filtered_images, key=itemgetter('pubDate'), reverse=True)
    return sorted_images

# Progress bar images
def count_images_by_media():
    count = session.query(ImageDataDB.media, func.count(ImageDataDB.id)).group_by(ImageDataDB.media).all()
    count_media_dict = {media: count for media, count in count}
    return count_media_dict 

@app.get("/images/media_count") 
async def count_media():
    count_media_dict = count_images_by_media()
    return count_media_dict



# carousel images 
@app.get("/images/latest_by_media")
async def get_latest_images_by_media():
    latest_images_by_media = {}

    media_list = session.query(ImageDataDB.media).distinct().all()
    for media in media_list:
        media_name = media[0]
        latest_images = session.query(ImageDataDB).filter_by(media=media_name).order_by(ImageDataDB.id.desc()).limit(5).all()
        
        latest_images_schema = [ImageData.from_orm(image) for image in latest_images]
        filtered_images = [image for image in latest_images_schema if getattr(image, "picture") is not None]
        latest_images_by_media[media_name] = filtered_images
        

    return latest_images_by_media




def group_images_by_section_pubdate_media(db: Session):
    grouped_images = {}

    images = db.query(ImageDataDB).all()

    # Trier les images par ID
    sorted_images = sorted(images, key=lambda x: x.id, reverse=True)

    # Parcourir les images triées
    for image in sorted_images:
        section_title = image.sectionTitle

        # Vérifier si la sectionTitle n'existe pas encore dans le dictionnaire
        if section_title not in grouped_images:
            grouped_images[section_title] = image

    return grouped_images



@app.get("/images/grouped")
async def get_grouped_images():
    grouped_images = group_images_by_section_pubdate_media(session)
    return grouped_images


@app.post("/images/{image_id}/rate")
async def vote_for_image(image_id: int):
    image = session.query(ImageDataDB).get(image_id)
    if image:
        if image.rates is None:
            image.rates = 0
        image.rates += 1
        session.commit()
        return {"message": "Vote added successfully."}
    else:
        return {"message": "Image not found."}
    
@app.get("/media")
async def get_media_list():
    media_list = session.query(ImageDataDB.media).distinct().all()
    return {"media": [media[0] for media in media_list]}






