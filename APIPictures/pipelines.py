# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import sqlite3

class ApipicturesPipeline:
    
    def __init__(self):
        #create connect to database
        self.con = sqlite3.connect('gallery.db')
        
        ## Create cursor, used to execute commands
        self.cur = self.con.cursor()
        
        ## Create quotes table if none exists
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS galleryTable(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media TEXT,
            sectionTitle TEXT,
            pubDate TEXT,
            pageUrl TEXT,
            caption TEXT,
            location TEXT,
            author TEXT,
            credits TEXT,
            picture TEXT,
        CONSTRAINT unique_caption_picture UNIQUE (caption, picture)
        )
        """)
           
    
    def process_item(self, item, spider):
        # Vérifier l'existence de l'enregistrement basé sur les colonnes spécifiées
        existing_record = self.cur.execute("""
            SELECT * FROM galleryTable WHERE caption = ? AND picture = ?
        """, (item['caption'], item['picture'])).fetchone()

        if existing_record:
            # Enregistrement existant, éviter l'insertion du doublon
            return item
        else:
            # Insérer le nouvel enregistrement dans la base de données
        
            self.cur.execute("""
                INSERT INTO galleryTable (media, sectionTitle, pubDate, pageUrl, caption, location, author, credits, picture) VALUES (?, ?, ?, ?, ?, ?, ? , ?, ?)
            """,
            (
                item['media'],
                item['sectionTitle'],
                item['pubDate'],
                item['pageUrl'],
                item['caption'], 
                item['location'],
                item['author'],
                item['credits'],
                item['picture']
                
            ))

            
            self.con.commit()
            return item
