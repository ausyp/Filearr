import os
from typing import List, Dict
import platform

class DirectoryService:
    @staticmethod
    def list_directories(path: str) -> Dict:
        """
        Lists directories and files in a given path.
        Returns a dictionary with 'current_path', 'parent_path', 'directories', and 'files'.
        """
        if not path or not os.path.exists(path):
            # Default to root or home if path is invalid
            path = "/" if platform.system() != "Windows" else "C:\\"
        
        # Normalize path
        path = os.path.abspath(path)
        
        directories = []
        files = []
        
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir():
                        directories.append(entry.name)
                    else:
                        files.append(entry.name)
        except PermissionError:
            return {"error": "Permission denied"}
        except Exception as e:
            return {"error": str(e)}
            
        # Sort for better UX
        directories.sort()
        files.sort()
        
        parent_path = os.path.dirname(path)
        
        return {
            "current_path": path,
            "parent_path": parent_path,
            "directories": directories,
            "files": files 
        }

directory_service = DirectoryService()
