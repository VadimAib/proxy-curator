                                                                 

                                                                                                                        
                                   
   
from typing import Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def _read_modes(args: "argparse.Namespace") -> Tuple[bool, bool]:
                                                              

                                                                             
                                                                             
                                                                      
                                                                            
                                                                              
                                                                             
                    

                                                                         
                                                                               

                                                                             
                                                       
       
    return (bool(getattr(args, "tcping_only", False)),
            bool(getattr(args, "ping_only", False)))
