                                                 

                                                                           
                                                                           
                                                                             
                                                                          

                                                                            
                                           

                                                                       
                                                                           
   
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def rp(p: str) -> Path:
                                                                                                                                     
    path = Path(p)
    return path if path.is_absolute() else ROOT / path
