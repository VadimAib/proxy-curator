                                                                              

                                                                                  
                                                                       
                                                                         
                                                                        
             

                                                                        
                                                                     
                     
                                                                                
                                            
                                                                      
                                                                           
                                                                     
                                                               
                                                            
                                                                     
                                                             
                                                          
                                                                      
                                                                        
                                                                          
                      

                                                                  
                                                                       
                                                                          
                                                                    
                                            

                                                                         
                                                                 
                                                                 
                                                                    
                                                                      
                                                               
                                                                 
                           

                                                                            
                                                                         
            
   
import shutil
from pathlib import Path
from typing import List, Tuple

from .log import LOG
from .net.netlabel import safe_dirname





ARCHIVED_FILES = (
    "summary.json",
    "diag_tls_ok.txt",
    "working_nodes.json",
    "unparseable_sample.txt",
)





MERGE_REFRESH_FILES = ("working_nodes.json", "summary.json")








def archive_run_artifacts(out_dir: Path, network: str,
                         files: Tuple[str, ...] = ARCHIVED_FILES) -> List[Path]:
                                                              

                                                                     
                                                                    
                                                                          
                                                

                                                                       
                                                                         
                                                                    

                                                                         
                                                              
       
    dest = Path(out_dir) / safe_dirname(network)
    copied: List[Path] = []
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        LOG(f"[archive] WARNING: cannot create {dest}: {e}")
        return copied

    for name in _sources(Path(out_dir), files):
        try:
            shutil.copy2(name, dest / name.name)
            copied.append(dest / name.name)
        except OSError as e:

            LOG(f"[archive] WARNING: {name.name} not copied: {e}")
    if copied:
        LOG(f"[archive] {len(copied)} file(s) -> {dest.name}/: "
            + ", ".join(p.name for p in copied))
    else:
        LOG(f"[archive] nothing to archive -> {dest.name}/")
    return copied


def _sources(out_dir: Path,
             files: Tuple[str, ...] = ARCHIVED_FILES) -> List[Path]:
                                          

                                                                        
                                                     
                                                      
                                                                 
                                                                         
                             
       
    found: List[Path] = []
    for name in files:
        path = out_dir / name
        if path.is_file():
            found.append(path)
    return found
