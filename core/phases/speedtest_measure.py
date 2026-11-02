                                                      

                                     

                                                                            
                                                                                 
                                                                 
                                                                        
                                                              

                                                                            
                                                                            
                                                                         
   
from __future__ import annotations

from .speedtest_channel import (_detect_channel_profile_from_state,
                                _download_via_proxy, _measure_one,
                                _run_speed_via_engine, _run_tier)
from .speedtest_instrument import (_CAP_SLACK, _MIN_TRANSFER_DEADLINE,
                                   _READ_CHUNK, _READ_TIMEOUT_MARKERS,
                                   _TIMEOUT_ESCALATION,
                                   _TRANSFER_DEADLINE_FACTOR, calc_mbps,
                                   escalation_saved, timeout_for_budget,
                                   transfer_deadline)
from .speedtest_instrument import _reset_escalation_counter
