                                                                  

                                                                       
                                                                            
                                                                         
                                
   
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import Node


@dataclass
class PipelineState:
                                       

                                                        
                                                                        
                                                                             
                                                     
                                                                               
                                                                         
                                                         
                                                                              
                                                     
                                                                             
                                                                        
                                                                           
                                                                               
                                                                      
                                                                             
                                                                                  
                                                                         
                                                                         
                                                                              
                                                                           
                                                                           
                                                               
                                                                       
                                                                     
                                                                               
                                                                       
                                                                            
                                                                          
                                                                 
                                                          
                                                                            
                                                       
                                                 
                                                                   
                                                             
                                                                        
                                                                          
                               

                                                                            
                                                                     
                                                           
                                                                               
                                                                         
                                                                             
                                                                             
                                                                      
                                                      

                                                                                
                                                                             
                                                                         
                                                                               
                                                                         
                                                       
       

    links: List[str] = field(default_factory=list)
    config_nodes: List[Node] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)
    policy_drops: Dict[str, int] = field(default_factory=dict)




    link_source: Dict[str, str] = field(default_factory=dict)







    feed_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    source_nodes: List[Node] = field(default_factory=list)
    nodes: List[Node] = field(default_factory=list)
    alive: List[Tuple[Node, float]] = field(default_factory=list)
    final: List[Tuple[Node, float]] = field(default_factory=list)
    quick_pool: List[Tuple[Node, float]] = field(default_factory=list)
    conn_drops: Dict[str, Tuple[Node, str]] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    resume_data: Optional[Dict[str, Any]] = None
    current_phase: str = ""


    save_checkpoint: bool = True

    def bump_feed(self, src: Optional[str], key: str,
                  amount: int = 1) -> None:
                                                               

                                                               
                                                                       
                                                                 
                                                                     
                                                                  
                                                                   
                                                                    
           
        if src:
            row = self.feed_stats.setdefault(src, {})
            row[key] = row.get(key, 0) + amount
