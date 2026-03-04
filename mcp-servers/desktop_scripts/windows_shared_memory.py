"""
Windows Shared Memory Reader
HWiNFOとMSI AfterburnerのShared Memoryからデータを読み取る
"""

import ctypes
import struct
import logging
from typing import Dict, Optional, Any
from ctypes import wintypes

logger = logging.getLogger(__name__)

# Windows API定数
FILE_MAP_READ = 0x0001
INVALID_HANDLE_VALUE = -1
PAGE_READONLY = 0x02
ERROR_FILE_NOT_FOUND = 2


class WindowsSharedMemory:
    """Windows Shared Memory Reader"""
    
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self._setup_functions()
    
    def _setup_functions(self):
        """Windows API関数を設定"""
        # OpenFileMapping
        self.kernel32.OpenFileMappingW.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.LPCWSTR
        ]
        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        
        # MapViewOfFile
        self.kernel32.MapViewOfFile.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_size_t
        ]
        self.kernel32.MapViewOfFile.restype = wintypes.LPVOID
        
        # UnmapViewOfFile
        self.kernel32.UnmapViewOfFile.argtypes = [wintypes.LPVOID]
        self.kernel32.UnmapViewOfFile.restype = wintypes.BOOL
        
        # CloseHandle
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
    
    def read_shared_memory(self, name: str, size: int) -> Optional[bytes]:
        """Shared Memoryからデータを読み取り"""
        try:
            # Shared Memoryを開く
            h_map = self.kernel32.OpenFileMappingW(
                FILE_MAP_READ,
                False,
                name
            )
            
            if h_map == INVALID_HANDLE_VALUE or h_map == 0:
                return None
            
            try:
                # メモリをマップ
                p_buf = self.kernel32.MapViewOfFile(
                    h_map,
                    FILE_MAP_READ,
                    0,
                    0,
                    size
                )
                
                if not p_buf:
                    return None
                
                try:
                    # データを読み取り
                    buffer = ctypes.create_string_buffer(size)
                    ctypes.memmove(buffer, p_buf, size)
                    return buffer.raw
                finally:
                    self.kernel32.UnmapViewOfFile(p_buf)
            finally:
                self.kernel32.CloseHandle(h_map)
        except Exception as e:
            logger.error(f"Failed to read shared memory {name}: {e}")
            return None


class HWiNFOMemoryReader:
    """HWiNFO Shared Memory Reader"""
    
    # HWiNFO Shared Memory名
    HWiNFO_SENSORS_STRING = "HWiNFO_SENSORS_SM2"
    HWiNFO_SENSORS_SIZE = 0x10000  # 64KB
    
    def __init__(self):
        self.shm = WindowsSharedMemory()
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """HWiNFO Shared Memoryの可用性を確認"""
        data = self.shm.read_shared_memory(
            self.HWiNFO_SENSORS_STRING,
            self.HWiNFO_SENSORS_SIZE
        )
        self.is_available = data is not None
        if self.is_available:
            logger.info("HWiNFO Shared Memory is available")
        else:
            logger.debug("HWiNFO Shared Memory is not available")
    
    def read_sensors(self) -> Dict[str, Any]:
        """センサーデータを読み取り"""
        if not self.is_available:
            return {}
        
        data = self.shm.read_shared_memory(
            self.HWiNFO_SENSORS_STRING,
            self.HWiNFO_SENSORS_SIZE
        )
        
        if not data:
            return {}
        
        try:
            # HWiNFO Shared Memory構造を解析
            # 注意: HWiNFOのShared Memory構造は非公開のため、
            # 実際の構造に合わせて調整が必要
            
            # 基本構造（推測）
            # Offset 0x0: バージョン情報
            # Offset 0x4: センサー数
            # Offset 0x8以降: センサーデータ
            
            result = {}
            
            # 簡易的な実装（実際の構造に合わせて調整が必要）
            # ここでは、nvidia-smiなどの代替手段を使用することを推奨
            
            return result
        except Exception as e:
            logger.error(f"Failed to parse HWiNFO data: {e}")
            return {}


class RTSSMemoryReader:
    """RivaTuner Statistics Server (MSI Afterburner) Shared Memory Reader"""
    
    RTSS_SHARED_MEMORY = "RTSSSharedMemoryV2"
    RTSS_SHARED_MEMORY_SIZE = 0x10000  # 64KB
    
    # RTSS Shared Memory構造（推測）
    RTSS_OFFSET_VERSION = 0x0
    RTSS_OFFSET_APP_NAME = 0x4
    RTSS_OFFSET_DATA = 0x100
    
    def __init__(self):
        self.shm = WindowsSharedMemory()
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """RTSS Shared Memoryの可用性を確認"""
        data = self.shm.read_shared_memory(
            self.RTSS_SHARED_MEMORY,
            self.RTSS_SHARED_MEMORY_SIZE
        )
        self.is_available = data is not None
        if self.is_available:
            logger.info("RTSS Shared Memory is available")
        else:
            logger.debug("RTSS Shared Memory is not available")
    
    def read_metrics(self) -> Dict[str, Any]:
        """メトリクスを読み取り"""
        if not self.is_available:
            return {}
        
        data = self.shm.read_shared_memory(
            self.RTSS_SHARED_MEMORY,
            self.RTSS_SHARED_MEMORY_SIZE
        )
        
        if not data:
            return {}
        
        try:
            # RTSS Shared Memory構造を解析
            # 注意: RTSSのShared Memory構造は非公開のため、
            # 実際の構造に合わせて調整が必要
            
            result = {}
            
            # 簡易的な実装（実際の構造に合わせて調整が必要）
            # ここでは、nvidia-smiなどの代替手段を使用することを推奨
            
            return result
        except Exception as e:
            logger.error(f"Failed to parse RTSS data: {e}")
            return {}


if __name__ == "__main__":
    # テスト
    logging.basicConfig(level=logging.DEBUG)
    
    hwinfo = HWiNFOMemoryReader()
    print(f"HWiNFO available: {hwinfo.is_available}")
    if hwinfo.is_available:
        print(f"HWiNFO sensors: {hwinfo.read_sensors()}")
    
    rtss = RTSSMemoryReader()
    print(f"RTSS available: {rtss.is_available}")
    if rtss.is_available:
        print(f"RTSS metrics: {rtss.read_metrics()}")




