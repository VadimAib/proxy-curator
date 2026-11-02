                                                                   

                                                       

                                                                     
                                                                 
                    
                                                                 
                             

                                                                     
                                                                      
                                         
   
from typing import Optional


SPEED_PROFILES = ("auto", "full", "light")



CHANNEL_TO_SPEED_PROFILE = {
    "full": "full",
    "light": "light",
    "unknown": "full",
}


def normalize_speed_profile(raw: object) -> Optional[str]:
                                                                

                                                                           
             
       
    text = str(raw or "").strip().lower()
    if text in SPEED_PROFILES:
        return text
    return None


def speed_profile_for_channel(channel: object) -> str:
                                                                                                          
    return CHANNEL_TO_SPEED_PROFILE.get(
        str(channel or "").strip().lower(), "full")
