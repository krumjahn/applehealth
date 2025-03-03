from django.core.files.storage import Storage
from django.db import connection
from django.utils.deconstruct import deconstructible
import base64
import os

@deconstructible
class PostgreSQLStorage(Storage):
    """
    Custom storage backend that stores files in PostgreSQL database.
    """
    
    def __init__(self):
        pass
        
    def _open(self, name, mode='rb'):
        """
        Retrieve the file from the database.
        """
        from io import BytesIO
        
        cursor = connection.cursor()
        cursor.execute(
            "SELECT content FROM file_uploads WHERE name = %s",
            [name]
        )
        row = cursor.fetchone()
        
        if row is None:
            raise FileNotFoundError(f"File {name} does not exist")
            
        content = base64.b64decode(row[0])
        return BytesIO(content)
        
    def _save(self, name, content):
        """
        Save the file to the database.
        """
        # Read file content
        content.seek(0)
        file_content = content.read()
        
        # Encode file content as base64
        encoded_content = base64.b64encode(file_content).decode('ascii')
        
        cursor = connection.cursor()
        
        # Check if file already exists
        cursor.execute(
            "SELECT COUNT(*) FROM file_uploads WHERE name = %s",
            [name]
        )
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Update existing file
            cursor.execute(
                "UPDATE file_uploads SET content = %s WHERE name = %s",
                [encoded_content, name]
            )
        else:
            # Insert new file
            cursor.execute(
                "INSERT INTO file_uploads (name, content) VALUES (%s, %s)",
                [name, encoded_content]
            )
            
        return name
        
    def delete(self, name):
        """
        Delete the file from the database.
        """
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM file_uploads WHERE name = %s",
            [name]
        )
        
    def exists(self, name):
        """
        Check if the file exists in the database.
        """
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM file_uploads WHERE name = %s",
            [name]
        )
        count = cursor.fetchone()[0]
        return count > 0
        
    def url(self, name):
        """
        Return URL for accessing the file.
        """
        from django.urls import reverse
        return reverse('file_download', kwargs={'path': name})
        
    def size(self, name):
        """
        Return the size of the file.
        """
        cursor = connection.cursor()
        cursor.execute(
            "SELECT LENGTH(DECODE(content, 'base64')) FROM file_uploads WHERE name = %s",
            [name]
        )
        row = cursor.fetchone()
        
        if row is None:
            raise FileNotFoundError(f"File {name} does not exist")
            
        return row[0]
        
    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's free on the target storage system.
        """
        # If the filename already exists, add an underscore and a number (e.g. 'file_1.txt')
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        
        count = 0
        while self.exists(name):
            count += 1
            name = os.path.join(dir_name, f"{file_root}_{count}{file_ext}")
            
        return name
