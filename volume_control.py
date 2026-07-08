"""
장치별(재생/녹음) 볼륨을 조회하고 설정하는 모듈.
IAudioEndpointVolume COM 인터페이스를 통해 특정 장치의 마스터 볼륨을 직접 제어한다.
(현재 시스템 기본 장치의 볼륨만 조절하는 게 아니라, 장치 ID를 지정해서 조절 가능)

이 모듈의 함수들은 pywebview의 JS-Python 브리지 콜백 스레드 등 어떤 스레드에서
호출될지 알 수 없으므로, 매 호출마다 자체적으로 COM을 초기화/해제한다.
"""

import comtypes
from ctypes import POINTER, cast

from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def _get_endpoint_volume(device_id: str):
    enumerator = AudioUtilities.GetDeviceEnumerator()
    device = enumerator.GetDevice(device_id)
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_volume_percent(device_id: str) -> int:
    """0~100 범위의 정수 퍼센트로 반환. 실패 시 0."""
    comtypes.CoInitialize()
    try:
        volume = _get_endpoint_volume(device_id)
        return round(volume.GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return 0
    finally:
        comtypes.CoUninitialize()


def set_volume_percent(device_id: str, percent: int):
    percent = max(0, min(100, percent))
    comtypes.CoInitialize()
    try:
        volume = _get_endpoint_volume(device_id)
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
    except Exception:
        pass
    finally:
        comtypes.CoUninitialize()


def get_mute(device_id: str) -> bool:
    comtypes.CoInitialize()
    try:
        volume = _get_endpoint_volume(device_id)
        return bool(volume.GetMute())
    except Exception:
        return False
    finally:
        comtypes.CoUninitialize()


def set_mute(device_id: str, mute: bool):
    comtypes.CoInitialize()
    try:
        volume = _get_endpoint_volume(device_id)
        volume.SetMute(1 if mute else 0, None)
    except Exception:
        pass
    finally:
        comtypes.CoUninitialize()


def toggle_mute(device_id: str) -> bool:
    """음소거 상태를 뒤집고, 뒤집은 뒤의 새 상태(True=음소거됨)를 반환한다."""
    new_state = not get_mute(device_id)
    set_mute(device_id, new_state)
    return new_state
