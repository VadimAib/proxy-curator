                                                                     

                                                                     
                                                                                
                                                                            
                                                          

           
                                                                            
                                                                           
                                                                           
                                                          
                                                                   
                                                                            
                                                                            
                                                         
                                                                            
                                             

                                                                                             
                                                                             
                                                        
   
import ctypes
from ctypes import wintypes

from ..log import dlog
from ..utils import first_line




JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JobObjectExtendedLimitInformation = 9

class _BasicLimitInfo(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimitInfo(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInfo),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


_job_handle = None


def assign_to_job(proc) -> None:
                                                                                                                         
    global _job_handle
    if _job_handle is None:
        k32 = ctypes.windll.kernel32
        h = k32.CreateJobObjectW(None, None)
        if h:
            info = _ExtendedLimitInfo()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if k32.SetInformationJobObject(
                h, _JobObjectExtendedLimitInformation,
                ctypes.byref(info), ctypes.sizeof(info)
            ):
                _job_handle = h
        if _job_handle is None:
            _job_handle = 0
    if _job_handle:
        try:
            ctypes.windll.kernel32.AssignProcessToJobObject(
                _job_handle, wintypes.HANDLE(proc._handle))
        except Exception as e:


            dlog(f"AssignProcessToJobObject failed: {first_line(e)}")
